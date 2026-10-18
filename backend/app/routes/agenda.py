"""Agenda escolar (PB13) e calendário de provas (PB16) — módulo Agenda e Calendário Escolar (Sprint 06).

Somente leitura: junta aulas, atividades, avaliações e eventos no recorte de cada perfil (ver services/agenda.py).
O cadastro de avaliações fica em /api/avaliacoes e o dos eventos em /api/eventos.
"""
from datetime import date

from flask import Blueprint, g, jsonify, request

from ..errors import ApiError
from ..security import auth_required
from ..services import agenda as ag

bp = Blueprint("agenda", __name__, url_prefix="/api/agenda")


@bp.get("")
@auth_required()
def listar():
    hoje = date.today()
    inicio = request.args.get("inicio") or hoje.isoformat()
    fim = request.args.get("fim") or inicio
    tipos = [t.strip().upper() for t in (request.args.get("tipos") or "").split(",") if t.strip()] or None
    if tipos and any(t not in ag.TIPOS_ITEM for t in tipos):
        raise ApiError(400, f"tipos deve conter apenas: {', '.join(ag.TIPOS_ITEM)}")
    lista = ag.itens(g.user, inicio, fim, tipos, request.args.get("idAluno", type=int), request.args.get("idTurma", type=int))
    return jsonify(inicio=inicio, fim=fim, itens=lista)


@bp.get("/proximos")
@auth_required()
def proximos():
    dias = min(max(request.args.get("dias", 14, type=int), 1), 60)
    limite = min(max(request.args.get("limite", 6, type=int), 1), 30)
    return jsonify(ag.proximos(g.user, dias, limite))


@bp.get("/provas")
@auth_required()
def provas():
    periodo = request.args.get("periodo", "proximas")
    if periodo not in ("proximas", "passadas", "todas"):
        raise ApiError(400, "periodo deve ser: proximas, passadas ou todas")
    bim = request.args.get("bimestre", type=int)
    if bim is not None and not 1 <= bim <= 4:
        raise ApiError(400, "Bimestre deve estar entre 1 e 4")
    return jsonify(ag.provas(g.user, request.args.get("idAluno", type=int), request.args.get("idTurma", type=int),
                             request.args.get("idTurmaDisciplina", type=int), bim, periodo))
