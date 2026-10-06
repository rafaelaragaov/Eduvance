"""Notificações internas (PB21) — módulo Comunicação Escolar (Sprint 05). Cada usuário acessa só as suas."""
from flask import Blueprint, g, jsonify, request

from ..db import execute, one, rows, scalar
from ..errors import nao_encontrado
from ..security import auth_required

bp = Blueprint("notificacoes", __name__, url_prefix="/api/notificacoes")


def _minha(id_: int) -> dict:
    n = one("SELECT id_notificacao FROM notificacao WHERE id_notificacao = ? AND id_usuario = ?", (id_, g.user["id"]))
    if not n:
        raise nao_encontrado("Notificação", feminino=True)
    return n


@bp.get("")
@auth_required()
def listar():
    where, params = "id_usuario = ?", [g.user["id"]]
    if request.args.get("naoLidas") in ("1", "true"):
        where += " AND lida = 0"
    limite = min(max(request.args.get("limite", 50, type=int), 1), 200)
    itens = rows(
        f"""SELECT id_notificacao AS id, tipo, titulo, mensagem, link, lida, criada_em AS criadaEm
              FROM notificacao WHERE {where} ORDER BY criada_em DESC, id_notificacao DESC LIMIT ?""",
        (*params, limite),
    )
    for n in itens:
        n["lida"] = bool(n["lida"])
    nao_lidas = scalar("SELECT COUNT(*) FROM notificacao WHERE id_usuario = ? AND lida = 0", (g.user["id"],))
    return jsonify(naoLidas=nao_lidas, itens=itens)


@bp.get("/contagem")
@auth_required()
def contagem():
    return jsonify(naoLidas=scalar("SELECT COUNT(*) FROM notificacao WHERE id_usuario = ? AND lida = 0", (g.user["id"],)))


@bp.put("/lidas")
@auth_required()
def marcar_todas():
    execute("UPDATE notificacao SET lida = 1 WHERE id_usuario = ? AND lida = 0", (g.user["id"],))
    return jsonify(naoLidas=0)


@bp.put("/<int:id_>/lida")
@auth_required()
def marcar_lida(id_):
    _minha(id_)
    execute("UPDATE notificacao SET lida = 1 WHERE id_notificacao = ?", (id_,))
    return jsonify(naoLidas=scalar("SELECT COUNT(*) FROM notificacao WHERE id_usuario = ? AND lida = 0", (g.user["id"],)))


@bp.delete("/<int:id_>")
@auth_required()
def excluir(id_):
    _minha(id_)
    execute("DELETE FROM notificacao WHERE id_notificacao = ?", (id_,))
    return "", 204
