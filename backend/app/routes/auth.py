from flask import Blueprint, g, jsonify, request

from ..db import one
from ..errors import ApiError, Corpo
from ..security import auth_required, confere_senha, gerar_token, limitar_login
from ..services.usuarios import usuario_por_id

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    """Login por e-mail OU matrícula (aluno) + senha, validado contra o banco de dados."""
    limitar_login()
    c = Corpo(request.get_json(silent=True))
    ident = c.texto("identificador", "E-mail ou matrícula")
    senha = c.texto("senha", "Senha", maximo=200)
    c.validar()

    u = one(
        """SELECT u.id_usuario AS id, u.perfil, u.senha_hash, u.ativo
             FROM usuario u LEFT JOIN aluno a ON a.id_aluno = u.id_usuario
            WHERE lower(u.email) = lower(?) OR a.matricula = ?
            LIMIT 1""",
        (ident, ident),
    )
    ok = confere_senha(senha, u["senha_hash"] if u else None)
    if not u or not ok or not u["ativo"]:
        raise ApiError(401, "Credenciais inválidas")
    return jsonify(token=gerar_token(u["id"], u["perfil"]), usuario=usuario_por_id(u["id"]))


@bp.get("/me")
@auth_required()
def me():
    return jsonify(usuario=usuario_por_id(g.user["id"]))
