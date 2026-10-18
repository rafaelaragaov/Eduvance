"""Preferências do usuário (página Configurações, Sprint 06): tamanho da fonte e tema, salvos por usuário no banco
para acompanhar a pessoa em qualquer dispositivo."""
from flask import Blueprint, g, jsonify, request

from ..db import execute, one
from ..errors import ApiError
from ..security import auth_required

bp = Blueprint("preferencias", __name__, url_prefix="/api/preferencias")

FONTES = [85, 100, 115, 130, 150]   # % do tamanho padrão do texto
TEMAS = ["claro", "escuro", "auto"]
PADRAO = {"fonte": 100, "tema": "auto"}


def _atuais(id_usuario: int) -> dict:
    """Preferências salvas; `salvo` diz se a pessoa já escolheu algo (o front-end então envia o que escolheu antes do login)."""
    r = one("SELECT fonte, tema FROM preferencia_usuario WHERE id_usuario = ?", (id_usuario,))
    return {**(r or PADRAO), "salvo": bool(r)}


@bp.get("")
@auth_required()
def obter():
    return jsonify(_atuais(g.user["id"]))


@bp.put("")
@auth_required()
def salvar():
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict):
        raise ApiError(400, "Corpo da requisição deve ser um objeto JSON")
    novo = _atuais(g.user["id"])
    erros = []
    if "fonte" in corpo:
        if corpo["fonte"] not in FONTES or isinstance(corpo["fonte"], bool):
            erros.append({"campo": "fonte", "mensagem": f"Tamanho da fonte deve ser um de: {', '.join(map(str, FONTES))}"})
        else:
            novo["fonte"] = corpo["fonte"]
    if "tema" in corpo:
        if corpo["tema"] not in TEMAS:
            erros.append({"campo": "tema", "mensagem": f"Tema deve ser um de: {', '.join(TEMAS)}"})
        else:
            novo["tema"] = corpo["tema"]
    if erros:
        raise ApiError(400, "Dados inválidos", erros)
    execute(
        """INSERT INTO preferencia_usuario (id_usuario, fonte, tema, atualizada_em) VALUES (?,?,?, datetime('now','localtime'))
           ON CONFLICT(id_usuario) DO UPDATE SET fonte = excluded.fonte, tema = excluded.tema, atualizada_em = excluded.atualizada_em""",
        (g.user["id"], novo["fonte"], novo["tema"]),
    )
    return jsonify({"fonte": novo["fonte"], "tema": novo["tema"], "salvo": True})


@bp.delete("")
@auth_required()
def restaurar():
    """Volta ao padrão (fonte 100% e tema automático)."""
    execute("DELETE FROM preferencia_usuario WHERE id_usuario = ?", (g.user["id"],))
    return jsonify({**PADRAO, "salvo": False})
