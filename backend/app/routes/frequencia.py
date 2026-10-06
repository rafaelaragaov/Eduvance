"""Registro de frequência / chamada (PB12) — módulo Notas, Frequência e Boletim (Sprint 04).

 - PROFESSOR: registra a chamada das suas turmas/disciplinas.
 - COORDENADOR e ADMIN: registram e consultam todas.
"""
from datetime import date, datetime

from flask import Blueprint, current_app, g, jsonify, request

from ..db import one, rows, transacao
from ..errors import ApiError, Corpo
from ..security import auth_required
from ..services.acesso import pode_gerir_turma_disciplina
from ..services.comunicacao import notificar, responsaveis_do_aluno

bp = Blueprint("frequencia", __name__, url_prefix="/api/frequencia")


def _data(valor, campo="data") -> str:
    c = Corpo({campo: valor})
    d = c.data(campo, "Data")
    c.validar()
    dia = datetime.strptime(d, "%Y-%m-%d").date()
    if dia > date.today():
        raise ApiError(400, "Não é possível registrar frequência em data futura", [{"campo": campo, "mensagem": "A data não pode ser futura"}])
    if dia.weekday() >= 5:
        raise ApiError(400, "Não há aula aos sábados e domingos", [{"campo": campo, "mensagem": "Escolha um dia útil (segunda a sexta)"}])
    return d


def _td(id_td) -> dict:
    if not isinstance(id_td, int) or isinstance(id_td, bool):
        raise ApiError(400, "Turma/disciplina é obrigatória", [{"campo": "idTurmaDisciplina", "mensagem": "Turma/disciplina é obrigatória"}])
    td = one(
        """SELECT td.id_turma_disciplina AS id, t.nome AS turma, d.nome AS disciplina
             FROM turma_disciplina td JOIN turma t ON t.id_turma = td.id_turma
             JOIN disciplina d ON d.id_disciplina = td.id_disciplina WHERE td.id_turma_disciplina = ?""",
        (id_td,),
    )
    if not td:
        raise ApiError(404, "Turma/disciplina não encontrada")
    if not pode_gerir_turma_disciplina(g.user, id_td):
        raise ApiError(403, "Você não leciona esta disciplina nesta turma")
    return td


def _dia(td: dict, data: str) -> dict:
    minimo = current_app.config["FREQUENCIA_MINIMA"]
    min_aulas = current_app.config["MIN_AULAS_PARA_FALTA"]
    alunos = rows(
        """SELECT a.id_aluno AS idAluno, u.nome, a.matricula, fh.presente AS presente,
                  (SELECT COUNT(*) FROM frequencia f WHERE f.id_aluno = a.id_aluno AND f.id_turma_disciplina = ?) AS aulas,
                  (SELECT COUNT(*) FROM frequencia f WHERE f.id_aluno = a.id_aluno AND f.id_turma_disciplina = ? AND f.presente = 0) AS faltas
             FROM turma_disciplina td
             JOIN aluno a ON a.id_turma = td.id_turma
             JOIN usuario u ON u.id_usuario = a.id_aluno
             LEFT JOIN frequencia fh ON fh.id_aluno = a.id_aluno AND fh.id_turma_disciplina = td.id_turma_disciplina AND fh.data = ?
            WHERE td.id_turma_disciplina = ?
            ORDER BY u.nome""",
        (td["id"], td["id"], data, td["id"]),
    )
    for a in alunos:
        a["presente"] = None if a["presente"] is None else bool(a["presente"])
        a["frequencia"] = None if not a["aulas"] else round(100.0 * (a["aulas"] - a["faltas"]) / a["aulas"], 1)
        # mesma regra do boletim: só vale com um mínimo de aulas registradas (evita alarme com 1 falta em 2 aulas)
        a["abaixoDoMinimo"] = a["frequencia"] is not None and a["aulas"] >= min_aulas and a["frequencia"] < minimo
    registrada = any(a["presente"] is not None for a in alunos)
    return {
        "idTurmaDisciplina": td["id"], "turma": td["turma"], "disciplina": td["disciplina"], "data": data,
        "registrada": registrada, "frequenciaMinima": minimo, "alunos": alunos,
    }


@bp.get("")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def consultar():
    """Chamada de um dia (presença já registrada ou vazia) + acumulado de faltas por aluno."""
    td = _td(request.args.get("idTurmaDisciplina", type=int))
    data = _data(request.args.get("data", ""))
    return jsonify(_dia(td, data))


@bp.put("")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def registrar():
    """Grava a chamada completa do dia (todos os alunos da turma) numa única transação.

    Corpo: {"idTurmaDisciplina": 6, "data": "2026-10-05", "registros": [{"idAluno": 7, "presente": true}, ...]}
    """
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict):
        raise ApiError(400, "Corpo da requisição deve ser um objeto JSON")
    td = _td(corpo.get("idTurmaDisciplina"))
    data = _data(corpo.get("data"))
    regs = corpo.get("registros")
    if not isinstance(regs, list) or not regs:
        raise ApiError(400, "Informe a presença dos alunos", [{"campo": "registros", "mensagem": "Nenhum aluno informado"}])

    ids = [a["id_aluno"] for a in rows(
        "SELECT a.id_aluno FROM aluno a JOIN turma_disciplina td ON td.id_turma = a.id_turma WHERE td.id_turma_disciplina = ?", (td["id"],))]
    marcados: dict[int, bool] = {}
    erros = []
    for i, r in enumerate(regs):
        ida = r.get("idAluno") if isinstance(r, dict) else None
        pres = r.get("presente") if isinstance(r, dict) else None
        if not isinstance(ida, int) or isinstance(ida, bool) or ida not in ids:
            erros.append({"campo": f"registros[{i}]", "mensagem": "Aluno não pertence a esta turma"})
        elif not isinstance(pres, bool):
            erros.append({"campo": f"registros[{i}]", "mensagem": "Informe presente (verdadeiro) ou falta (falso)"})
        elif ida in marcados:
            erros.append({"campo": f"registros[{i}]", "mensagem": "Aluno informado mais de uma vez"})
        else:
            marcados[ida] = pres
    if erros:
        raise ApiError(400, "Há registros inválidos na chamada", erros)
    faltando = len(ids) - len(marcados)
    if faltando:
        raise ApiError(400, f"Informe a presença de todos os alunos da turma (faltam {faltando})",
                       [{"campo": "registros", "mensagem": f"Faltam {faltando} aluno(s) na chamada"}])

    min_aulas = current_app.config["MIN_AULAS_PARA_FALTA"]
    antes = {a["idAluno"]: a["abaixoDoMinimo"] for a in _dia(td, data)["alunos"]}
    with transacao() as con:
        for ida, pres in marcados.items():
            con.execute(
                """INSERT INTO frequencia (id_aluno, id_turma_disciplina, data, presente) VALUES (?,?,?,?)
                   ON CONFLICT (id_aluno, id_turma_disciplina, data) DO UPDATE SET presente = excluded.presente""",
                (ida, td["id"], data, 1 if pres else 0),
            )
    resultado = _dia(td, data)
    # Sprint 05: quem acabou de cair abaixo do mínimo de frequência avisa o aluno e os responsáveis (uma vez, na transição)
    alertados = 0
    for a in resultado["alunos"]:
        if a["abaixoDoMinimo"] and not antes.get(a["idAluno"]) and a["aulas"] >= min_aulas:
            alertados += notificar(
                [a["idAluno"], *responsaveis_do_aluno(a["idAluno"])], "FREQUENCIA",
                f"Frequência abaixo do mínimo — {td['disciplina']}",
                f"{a['nome']} está com {a['frequencia']:.1f}% de presença em {td['disciplina']}; o mínimo exigido é {current_app.config['FREQUENCIA_MINIMA']:g}%.",
                "/boletim",
            )
    resultado["alertas"] = alertados
    resultado["resumo"] = {"presentes": sum(marcados.values()), "faltas": len(marcados) - sum(marcados.values())}
    return jsonify(resultado)
