"""Senhas (hash), JWT e controle de acesso por perfil (RBAC)."""
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from .db import one
from .errors import ApiError, proibido

PERFIS = ("ADMIN", "COORDENADOR", "PROFESSOR", "ALUNO", "RESPONSAVEL")
_METODO_HASH = "pbkdf2:sha256:260000"


def hash_senha(senha: str) -> str:
    return generate_password_hash(senha, method=_METODO_HASH)


_HASH_FALSO = hash_senha("senha-ficticia")


def confere_senha(senha: str, hash_: str | None) -> bool:
    # Compara sempre (mesmo sem usuário) para não revelar por tempo de resposta se o login existe.
    ok = check_password_hash(hash_ or _HASH_FALSO, senha)
    return ok and hash_ is not None


def gerar_token(id_usuario: int, perfil: str) -> str:
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(id_usuario),
        "perfil": perfil,
        "iat": agora,
        "exp": agora + timedelta(hours=current_app.config["JWT_HORAS"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def _usuario_do_token() -> dict:
    cab = request.headers.get("Authorization", "")
    if not cab.startswith("Bearer "):
        raise ApiError(401, "Autenticação necessária")
    try:
        dados = jwt.decode(cab[7:], current_app.config["JWT_SECRET"], algorithms=["HS256"])
    except jwt.PyJWTError:
        raise ApiError(401, "Sessão expirada ou token inválido")
    # Confirma no banco que o usuário continua ativo e usa o perfil ATUAL do banco.
    u = one("SELECT id_usuario AS id, nome, perfil, ativo FROM usuario WHERE id_usuario = ?", (int(dados["sub"]),))
    if not u or not u["ativo"]:
        raise ApiError(401, "Usuário inexistente ou inativo")
    return {"id": u["id"], "nome": u["nome"], "perfil": u["perfil"]}


def auth_required(*perfis: str):
    """Decorator: exige token válido e, opcionalmente, um dos perfis informados."""

    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            g.user = _usuario_do_token()
            if perfis and g.user["perfil"] not in perfis:
                raise proibido()
            return fn(*a, **kw)

        return wrapper

    return deco


# ---------------------------------------------------------------------------
# Limitador simples de tentativas de login (por IP) - em memória.
_tentativas: dict[str, deque] = defaultdict(deque)


def limitar_login():
    ip = request.remote_addr or "?"
    agora = time.monotonic()
    fila = _tentativas[ip]
    while fila and agora - fila[0] > 60:
        fila.popleft()
    if len(fila) >= current_app.config["LOGIN_MAX_POR_MINUTO"]:
        raise ApiError(429, "Muitas tentativas de login. Aguarde um minuto e tente novamente.")
    fila.append(agora)
