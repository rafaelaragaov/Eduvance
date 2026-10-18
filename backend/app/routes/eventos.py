"""Calendário escolar (PB17) — módulo Agenda e Calendário Escolar (Sprint 06).

 - COORDENADOR e ADMIN: cadastram, alteram e cancelam eventos (reunião, conselho, feriado, recesso, evento).
 - Os demais perfis leem os eventos dirigidos a eles (mesmo critério de público dos comunicados).
 - Feriado e recesso valem para toda a escola e suspendem aulas e avaliações nesses dias.
 - Integração com Comunicação: criar, remarcar ou cancelar um evento notifica o público-alvo.
"""
import re
from datetime import date

from flask import Blueprint, g, jsonify, request

from ..db import execute, one, rows, scalar
from ..errors import ApiError, Corpo, nao_encontrado, proibido
from ..security import auth_required
from ..services import agenda as ag
from ..services import comunicacao as cm

bp = Blueprint("eventos", __name__, url_prefix="/api/eventos")

HORA_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_ROTULOS = {"EVENTO": "Evento", "REUNIAO": "Reunião", "CONSELHO": "Conselho de classe", "FERIADO": "Feriado", "RECESSO": "Recesso"}

_BASE = """
  SELECT c.id_evento AS id, c.titulo, c.descricao, c.inicio, c.fim, c.tipo, c.dia_inteiro AS diaInteiro,
         c.publico, c.id_turma AS idTurma, t.nome AS turma, c.id_usuario_autor AS idAutor,
         COALESCE(u.nome, 'Usuário removido') AS autor
    FROM evento c
    LEFT JOIN turma t ON t.id_turma = c.id_turma
    LEFT JOIN usuario u ON u.id_usuario = c.id_usuario_autor"""


def _fmt(e: dict, user: dict) -> dict:
    e["diaInteiro"] = bool(e["diaInteiro"])
    e["podeAlterar"] = user["perfil"] in ("ADMIN", "COORDENADOR")
    e["data"], e["hora"] = e["inicio"][:10], (None if e["diaInteiro"] else e["inicio"][11:16])
    e["dataFim"] = e["fim"][:10] if e["fim"] else None
    e["horaFim"] = e["fim"][11:16] if e["fim"] and not e["diaInteiro"] else None
    return e


def _visivel(id_: int) -> dict:
    filtro, p = cm.filtro_comunicados(g.user)
    e = one(_BASE + f" WHERE {filtro} AND c.id_evento = ?", (*p, id_))
    if not e:
        raise nao_encontrado("Evento")
    return e


def _corpo() -> dict:
    c = Corpo(request.get_json(silent=True))
    d = {
        "titulo": c.texto("titulo", "Título", minimo=3, maximo=120),
        "descricao": c.texto("descricao", "Descrição", maximo=1000, obrigatorio=False),
        "tipo": c.opcao("tipo", "Tipo", ag.TIPOS_EVENTO),
        "publico": c.opcao("publico", "Público", cm.PUBLICOS, obrigatorio=False, padrao="TODOS"),
        "idTurma": c.inteiro("idTurma", "Turma", obrigatorio=False),
        "data": c.data("data", "Data"),
        "dataFim": c.data("dataFim", "Data final", obrigatorio=False),
        "hora": c.texto("hora", "Hora", obrigatorio=False, maximo=5),
        "horaFim": c.texto("horaFim", "Hora final", obrigatorio=False, maximo=5),
    }
    for campo, rot in (("hora", "Hora"), ("horaFim", "Hora final")):
        if d[campo] and not HORA_RE.match(d[campo]):
            c._erro(campo, f"{rot} deve estar no formato HH:MM")
    if d["publico"] == "TURMA" and not d["idTurma"]:
        c._erro("idTurma", "Informe a turma")
    if d["publico"] != "TURMA":
        d["idTurma"] = None
    sem_aula = d["tipo"] in ag.SEM_AULA
    if sem_aula and d["publico"] != "TODOS":
        c._erro("publico", f"{_ROTULOS[d['tipo']]} vale para toda a escola")
    c.validar()

    d["diaInteiro"] = sem_aula or not d["hora"]
    if d["diaInteiro"]:
        d["hora"] = d["horaFim"] = None
    if d["dataFim"] and d["dataFim"] < d["data"]:
        raise ApiError(400, "Dados inválidos", [{"campo": "dataFim", "mensagem": "A data final deve ser igual ou posterior à inicial"}])
    if d["dataFim"] == d["data"] and not d["diaInteiro"] and d["horaFim"] and d["horaFim"] <= d["hora"]:
        raise ApiError(400, "Dados inválidos", [{"campo": "horaFim", "mensagem": "A hora final deve ser depois da hora inicial"}])
    if d["idTurma"] and not one("SELECT 1 FROM turma WHERE id_turma = ?", (d["idTurma"],)):
        raise ApiError(400, "Dados inválidos", [{"campo": "idTurma", "mensagem": "Turma inexistente"}])
    d["inicio"] = f"{d['data']}T{d['hora'] or '00:00'}:00"
    fim_data = d["dataFim"] or (d["data"] if d["horaFim"] else None)
    d["fim"] = f"{fim_data}T{d['horaFim'] or ('23:59' if d['diaInteiro'] else d['hora'])}:00" if fim_data else None
    return d


def _conflitos(d: dict, id_atual: int | None) -> None:
    """Feriado/recesso não pode cobrir dias que já têm avaliações marcadas; evento repetido é recusado."""
    if d["tipo"] in ag.SEM_AULA:
        ultimo = d["dataFim"] or d["data"]
        n = scalar("SELECT COUNT(*) FROM avaliacao WHERE data_avaliacao BETWEEN ? AND ?", (d["data"], ultimo))
        if n:
            raise ApiError(409, f"Há {n} avaliação(ões) marcada(s) neste período. Remarque-as no calendário de provas antes de cadastrar o {_ROTULOS[d['tipo']].lower()}.",
                           [{"campo": "data", "mensagem": "Existem avaliações marcadas neste período"}])
    dup = scalar("SELECT 1 FROM evento WHERE lower(titulo) = lower(?) AND inicio = ? AND id_evento <> COALESCE(?, 0)", (d["titulo"], d["inicio"], id_atual))
    if dup:
        raise ApiError(409, "Já existe um evento com este título nesta data e hora", [{"campo": "titulo", "mensagem": "Evento repetido"}])


def _avisar(titulo: str, mensagem: str, publico: str, id_turma: int | None) -> int:
    return cm.notificar(cm.destinatarios_comunicado(publico, id_turma), "AGENDA", titulo, mensagem, "/calendario", ignorar=g.user["id"])


def _quando(e: dict) -> str:
    base = ag.br(e["inicio"])
    if e.get("fim") and e["fim"][:10] != e["inicio"][:10]:
        base += f" a {ag.br(e['fim'])}"
    return base if e.get("dia_inteiro") or e.get("diaInteiro") else f"{base} às {e['inicio'][11:16]}"


@bp.get("")
@auth_required()
def listar():
    filtro, p = cm.filtro_comunicados(g.user)
    extra, params = "", []
    if request.args.get("inicio"):
        extra += " AND date(COALESCE(c.fim, c.inicio)) >= ?"
        params.append(request.args["inicio"])
    if request.args.get("fim"):
        extra += " AND date(c.inicio) <= ?"
        params.append(request.args["fim"])
    if request.args.get("tipo"):
        extra += " AND c.tipo = ?"
        params.append(request.args["tipo"])
    return jsonify([_fmt(e, g.user) for e in rows(_BASE + f" WHERE {filtro} {extra} ORDER BY c.inicio, c.id_evento", [*p, *params])])


@bp.get("/<int:id_>")
@auth_required()
def obter(id_):
    return jsonify(_fmt(_visivel(id_), g.user))


@bp.post("")
@auth_required("COORDENADOR", "ADMIN")
def criar():
    d = _corpo()
    _conflitos(d, None)
    novo = execute(
        """INSERT INTO evento (titulo, descricao, inicio, fim, tipo, dia_inteiro, publico, id_turma, id_usuario_autor)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (d["titulo"], d["descricao"], d["inicio"], d["fim"], d["tipo"], int(d["diaInteiro"]), d["publico"], d["idTurma"], g.user["id"]),
    )
    e = _fmt(one(_BASE + " WHERE c.id_evento = ?", (novo,)), g.user)
    e["notificados"] = _avisar(f"{_ROTULOS[d['tipo']]}: {d['titulo']}", f"{d['titulo']} — {_quando(e)}.", d["publico"], d["idTurma"])
    return jsonify(e), 201


@bp.put("/<int:id_>")
@auth_required("COORDENADOR", "ADMIN")
def atualizar(id_):
    atual = one(_BASE + " WHERE c.id_evento = ?", (id_,))
    if not atual:
        raise nao_encontrado("Evento")
    d = _corpo()
    if d["publico"] != atual["publico"] or d["idTurma"] != atual["idTurma"]:
        raise ApiError(409, "O público do evento não pode ser alterado depois de cadastrado. Cancele e crie outro evento.")
    _conflitos(d, id_)
    execute(
        "UPDATE evento SET titulo=?, descricao=?, inicio=?, fim=?, tipo=?, dia_inteiro=? WHERE id_evento=?",
        (d["titulo"], d["descricao"], d["inicio"], d["fim"], d["tipo"], int(d["diaInteiro"]), id_),
    )
    novo = _fmt(one(_BASE + " WHERE c.id_evento = ?", (id_,)), g.user)
    mudou_data = (atual["inicio"], atual["fim"]) != (d["inicio"], d["fim"])
    novo["notificados"] = 0
    if mudou_data or atual["titulo"] != d["titulo"]:
        novo["notificados"] = _avisar(f"{'Evento remarcado' if mudou_data else 'Evento atualizado'}: {d['titulo']}",
                                      f"{d['titulo']} — agora em {_quando(novo)}." if mudou_data else f"{d['titulo']} — {_quando(novo)}.",
                                      d["publico"], d["idTurma"])
    return jsonify(novo)


@bp.delete("/<int:id_>")
@auth_required("COORDENADOR", "ADMIN")
def excluir(id_):
    atual = one(_BASE + " WHERE c.id_evento = ?", (id_,))
    if not atual:
        raise nao_encontrado("Evento")
    execute("DELETE FROM evento WHERE id_evento = ?", (id_,))
    _avisar(f"Evento cancelado: {atual['titulo']}", f"{atual['titulo']} ({_quando(atual)}) foi cancelado.", atual["publico"], atual["idTurma"])
    return "", 204
