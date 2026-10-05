"""Cálculos acadêmicos: boletim, média, faltas, agenda do dia e próxima aula."""
from datetime import datetime, timedelta

from flask import current_app

from ..db import rows, scalar


def _arred1(n: float) -> float:
    # arredondamento "comercial" (meio para cima), evitando o arredondamento bancário do round()
    return int(n * 10 + 0.5 + 1e-9) / 10


def boletim(id_aluno: int, bimestre: int | None = None) -> list[dict]:
    cfg = current_app.config
    bimestre = bimestre or cfg["BIMESTRE_ATUAL"]
    linhas = rows(
        """SELECT td.id_turma_disciplina AS id, d.nome AS materia,
                  (SELECT AVG(n.valor) FROM avaliacao av JOIN nota n ON n.id_avaliacao = av.id_avaliacao
                    WHERE av.id_turma_disciplina = td.id_turma_disciplina AND av.bimestre = ?
                      AND n.id_aluno = a.id_aluno) AS nota,
                  (SELECT 100.0 * SUM(f.presente) / COUNT(*) FROM frequencia f
                    WHERE f.id_aluno = a.id_aluno AND f.id_turma_disciplina = td.id_turma_disciplina) AS frequencia
             FROM aluno a
             JOIN turma_disciplina td ON td.id_turma = a.id_turma
             JOIN disciplina d ON d.id_disciplina = td.id_disciplina
            WHERE a.id_aluno = ?
            ORDER BY td.id_turma_disciplina""",
        (bimestre, id_aluno),
    )
    saida = []
    for r in linhas:
        nota = None if r["nota"] is None else _arred1(r["nota"])
        saida.append({
            "idTurmaDisciplina": r["id"],
            "materia": r["materia"],
            "nota": nota,
            "frequencia": None if r["frequencia"] is None else int(r["frequencia"] + 0.5),
            "status": "Sem nota" if nota is None else ("Aprovado" if nota >= cfg["MEDIA_APROVACAO"] else "Recuperação"),
        })
    return saida


def media_geral(linhas: list[dict]) -> float | None:
    notas = [l["nota"] for l in linhas if l["nota"] is not None]
    return _arred1(sum(notas) / len(notas)) if notas else None


def faltas(id_aluno: int) -> int:
    return scalar("SELECT COUNT(*) FROM frequencia WHERE id_aluno = ? AND presente = 0", (id_aluno,)) or 0


def classifica_media(m: float | None) -> str:
    if m is None:
        return "Sem notas"
    if m >= 8:
        return "Excelente"
    if m >= current_app.config["MEDIA_APROVACAO"]:
        return "Regular"
    return "Atenção"


# ---------- agenda / horários ------------------------------------------------
def _status_aula(inicio: str, fim: str, agora: datetime) -> str:
    m = agora.hour * 60 + agora.minute
    hi, mi = map(int, inicio.split(":"))
    hf, mf = map(int, fim.split(":"))
    if m >= hf * 60 + mf:
        return "Concluída"
    if m >= hi * 60 + mi:
        return "Em andamento"
    return "Próxima"


def aulas_do_dia(turma_id: int | None = None, professor_id: int | None = None, agora: datetime | None = None) -> list[dict]:
    agora = agora or datetime.now()
    where, params = ["h.dia_semana = ?"], [agora.isoweekday()]
    if turma_id:
        where.append("td.id_turma = ?")
        params.append(turma_id)
    if professor_id:
        where.append("td.id_professor = ?")
        params.append(professor_id)
    linhas = rows(
        f"""SELECT h.id_horario AS idHorario, h.id_turma_disciplina AS idTurmaDisciplina,
                   h.hora_inicio AS inicio, h.hora_fim AS fim, h.sala,
                   t.nome AS turma, d.nome AS disciplina, u.nome AS professor
              FROM horario h
              JOIN turma_disciplina td ON td.id_turma_disciplina = h.id_turma_disciplina
              JOIN turma t ON t.id_turma = td.id_turma
              JOIN disciplina d ON d.id_disciplina = td.id_disciplina
              LEFT JOIN usuario u ON u.id_usuario = td.id_professor
             WHERE {' AND '.join(where)}
             ORDER BY h.hora_inicio, t.nome""",
        params,
    )
    for l in linhas:
        l["status"] = _status_aula(l["inicio"], l["fim"], agora)
    return linhas


_DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def proxima_aula(id_td: int, agora: datetime | None = None) -> str | None:
    """Ex.: 'Hoje, às 08:00', 'Amanhã, às 10:30', 'Qua, às 09:00'."""
    agora = agora or datetime.now()
    hs = rows("SELECT dia_semana, hora_inicio FROM horario WHERE id_turma_disciplina = ?", (id_td,))
    if not hs:
        return None
    min_agora = agora.hour * 60 + agora.minute
    for off in range(0, 8):
        dia = agora + timedelta(days=off)
        horas = sorted(h["hora_inicio"] for h in hs if h["dia_semana"] == dia.isoweekday())
        for h in horas:
            if off > 0 or int(h[:2]) * 60 + int(h[3:5]) > min_agora:
                quando = "Hoje" if off == 0 else "Amanhã" if off == 1 else _DIAS[dia.weekday()]
                return f"{quando}, às {h}"
    return None


def urgencia(data_entrega: str, status_entrega: str, agora: datetime | None = None) -> str:
    """Rótulo de prioridade dos cards.

    ENTREGUE (já feita) | ATRASADA (prazo vencido) | URGENTE (vence hoje)
    | PENDENTE (vence em até 3 dias) | PLANEJADA (depois disso).
    """
    if status_entrega in ("ENTREGUE", "CORRIGIDA"):
        return "ENTREGUE"
    agora = agora or datetime.now()
    prazo = datetime.fromisoformat(data_entrega)
    if prazo < agora:
        return "ATRASADA"
    dias = (prazo.date() - agora.date()).days
    if dias == 0:
        return "URGENTE"
    if dias <= 3:
        return "PENDENTE"
    return "PLANEJADA"
