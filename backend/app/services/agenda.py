"""Regras do módulo Agenda e Calendário Escolar (Sprint 06): agenda unificada (PB13), calendário de provas (PB16)
e calendário escolar (PB17), integrados às avaliações (Sprint 04) e às notificações/comunicados (Sprint 05).

A agenda junta quatro fontes numa linha do tempo só: AULA (horário semanal), ATIVIDADE (prazos de entrega),
AVALIACAO (provas, trabalhos, testes e projetos) e EVENTO (calendário escolar). Cada perfil enxerga o seu recorte:
aluno -> a própria turma; responsável -> a turma de cada filho; professor -> suas turmas/disciplinas;
coordenação e administração -> a escola toda.
"""
from datetime import date, datetime, timedelta

from ..db import get_db, one, rows, scalar
from ..errors import ApiError, proibido
from . import comunicacao as cm
from .acesso import alunos_vinculados, pode_ver_aluno

TIPOS_EVENTO = ["EVENTO", "REUNIAO", "CONSELHO", "FERIADO", "RECESSO"]
TIPOS_ITEM = ["AULA", "ATIVIDADE", "AVALIACAO", "EVENTO"]
SEM_AULA = ("FERIADO", "RECESSO")          # dias em que não há aulas nem avaliações
MAX_PROVAS_POR_DIA = 2                      # no máximo 2 provas por dia na mesma turma
MAX_DIAS_CONSULTA = 100

_LINKS = {"AULA": "/agenda", "ATIVIDADE": "/atividades", "AVALIACAO": "/provas", "EVENTO": "/calendario"}
_ORDEM = {"EVENTO": 0, "AVALIACAO": 1, "ATIVIDADE": 2, "AULA": 3}


def br(d: str | date) -> str:
    """'2026-10-20' -> '20/10'."""
    d = d if isinstance(d, date) else date.fromisoformat(str(d)[:10])
    return d.strftime("%d/%m")


# ---------------------------------------------------------------------------
# Escopo por perfil
# ---------------------------------------------------------------------------
def contextos(user: dict, id_aluno: int | None = None, id_turma: int | None = None) -> list[dict]:
    """Os 'pontos de vista' da agenda do usuário. Cada contexto filtra turma_disciplina (alias td)."""
    p = user["perfil"]
    if p == "ALUNO":
        a = one("SELECT a.id_turma AS t, u.nome FROM aluno a JOIN usuario u ON u.id_usuario = a.id_aluno WHERE a.id_aluno = ?", (user["id"],))
        return [{"idAluno": user["id"], "aluno": a["nome"] if a else None, "sql": "td.id_turma = ?", "params": [a["t"] if a else None]}]
    if p == "RESPONSAVEL":
        filhos = alunos_vinculados(user["id"])
        if id_aluno:
            if id_aluno not in [f["id"] for f in filhos]:
                raise proibido("Este aluno não está vinculado à sua conta")
            filhos = [f for f in filhos if f["id"] == id_aluno]
        out = []
        for f in filhos:
            t = scalar("SELECT id_turma FROM aluno WHERE id_aluno = ?", (f["id"],))
            out.append({"idAluno": f["id"], "aluno": f["nome"], "sql": "td.id_turma = ?", "params": [t]})
        return out
    if p == "PROFESSOR":
        sql, params = "td.id_professor = ?", [user["id"]]
    else:  # COORDENADOR / ADMIN
        sql, params = "1 = 1", []
    if id_aluno and p in ("PROFESSOR", "COORDENADOR", "ADMIN"):
        if not pode_ver_aluno(user, id_aluno):
            raise proibido("Você não tem acesso a este aluno")
        t = scalar("SELECT id_turma FROM aluno WHERE id_aluno = ?", (id_aluno,))
        sql += " AND td.id_turma = ?"
        params.append(t)
    elif id_turma:
        sql += " AND td.id_turma = ?"
        params.append(id_turma)
    return [{"idAluno": None, "aluno": None, "sql": sql, "params": params}]


def _intervalo(inicio: str, fim: str) -> tuple[date, date]:
    try:
        i, f = date.fromisoformat(inicio), date.fromisoformat(fim)
    except (TypeError, ValueError):
        raise ApiError(400, "Informe 'inicio' e 'fim' no formato AAAA-MM-DD")
    if f < i:
        raise ApiError(400, "A data final deve ser igual ou posterior à inicial")
    if (f - i).days > MAX_DIAS_CONSULTA:
        raise ApiError(400, f"O período máximo de consulta é de {MAX_DIAS_CONSULTA} dias")
    return i, f


# ---------------------------------------------------------------------------
# Dias sem aula (calendário escolar -> agenda/avaliações)
# ---------------------------------------------------------------------------
def dias_sem_aula(inicio: date, fim: date) -> dict[str, str]:
    """{'2026-11-02': 'Finados', ...} com os feriados/recessos (para todos) que cobrem o período."""
    out: dict[str, str] = {}
    for e in rows(
        """SELECT titulo, inicio, fim FROM evento
            WHERE tipo IN ('FERIADO','RECESSO') AND publico = 'TODOS'
              AND date(inicio) <= ? AND date(COALESCE(fim, inicio)) >= ?""",
        (fim.isoformat(), inicio.isoformat()),
    ):
        d, ultimo = date.fromisoformat(e["inicio"][:10]), date.fromisoformat((e["fim"] or e["inicio"])[:10])
        while d <= ultimo:
            if inicio <= d <= fim:
                out[d.isoformat()] = e["titulo"]
            d += timedelta(days=1)
    return out


def bloqueio(data: str) -> str | None:
    """Título do feriado/recesso que cai na data (ou None)."""
    d = date.fromisoformat(data[:10])
    return dias_sem_aula(d, d).get(d.isoformat())


def validar_data_avaliacao(data: str, id_turma: int, tipo: str, id_atual: int | None = None) -> None:
    """Regras do calendário de provas (PB16): dia útil, sem feriado/recesso e no máximo 2 provas/dia por turma."""
    d = date.fromisoformat(data)
    if d.weekday() >= 5:
        raise ApiError(400, "Dados inválidos", [{"campo": "dataAvaliacao", "mensagem": "Avaliações não podem ser marcadas no fim de semana"}])
    motivo = bloqueio(data)
    if motivo:
        raise ApiError(400, "Dados inválidos", [{"campo": "dataAvaliacao", "mensagem": f"Não há aula em {br(d)} ({motivo}); escolha outro dia"}])
    if tipo == "PROVA":
        n = scalar(
            """SELECT COUNT(*) FROM avaliacao av JOIN turma_disciplina td ON td.id_turma_disciplina = av.id_turma_disciplina
                WHERE td.id_turma = ? AND av.tipo = 'PROVA' AND av.data_avaliacao = ? AND av.id_avaliacao <> COALESCE(?, 0)""",
            (id_turma, data, id_atual),
        )
        if n >= MAX_PROVAS_POR_DIA:
            raise ApiError(409, f"A turma já tem {MAX_PROVAS_POR_DIA} provas marcadas para {br(d)}",
                           [{"campo": "dataAvaliacao", "mensagem": f"Limite de {MAX_PROVAS_POR_DIA} provas por dia nesta turma; escolha outra data"}])


# ---------------------------------------------------------------------------
# Agenda unificada
# ---------------------------------------------------------------------------
def itens(user: dict, inicio: str, fim: str, tipos: list[str] | None = None, id_aluno: int | None = None,
          id_turma: int | None = None) -> list[dict]:
    ini, fi = _intervalo(inicio, fim)
    tipos = [t for t in (tipos or TIPOS_ITEM) if t in TIPOS_ITEM]
    ctxs = contextos(user, id_aluno, id_turma)
    multiplos = len({c["idAluno"] for c in ctxs}) > 1
    saida: list[dict] = []

    def rotulo(c):  # só mostra o nome do aluno quando o responsável acompanha mais de um
        return c["aluno"] if multiplos else None

    for c in ctxs:
        if "AULA" in tipos:
            sem_aula = dias_sem_aula(ini, fi)
            horarios = rows(
                f"""SELECT h.id_horario, h.dia_semana, h.hora_inicio, h.hora_fim, h.sala, t.nome AS turma, d.nome AS disciplina,
                           u.nome AS professor, td.id_turma_disciplina AS td
                      FROM horario h JOIN turma_disciplina td ON td.id_turma_disciplina = h.id_turma_disciplina
                      JOIN turma t ON t.id_turma = td.id_turma JOIN disciplina d ON d.id_disciplina = td.id_disciplina
                      LEFT JOIN usuario u ON u.id_usuario = td.id_professor
                     WHERE {c['sql']}""",
                c["params"],
            )
            dia = ini
            while dia <= fi:
                if dia.isoformat() not in sem_aula:
                    for h in horarios:
                        if h["dia_semana"] == dia.isoweekday():
                            saida.append({
                                "id": f"aula-{h['id_horario']}-{dia.isoformat()}-{c['idAluno'] or 0}", "tipo": "AULA", "categoria": "AULA",
                                "titulo": h["disciplina"], "inicio": f"{dia.isoformat()}T{h['hora_inicio']}:00", "fim": f"{dia.isoformat()}T{h['hora_fim']}:00",
                                "diaInteiro": False, "turma": h["turma"], "disciplina": h["disciplina"], "professor": h["professor"],
                                "sala": h["sala"], "aluno": rotulo(c), "idAluno": c["idAluno"], "link": _LINKS["AULA"],
                            })
                dia += timedelta(days=1)

        if "ATIVIDADE" in tipos:
            ent_sel, ent_join, ent_params = ("'PENDENTE'", "", [])
            if c["idAluno"]:
                ent_sel = "COALESCE(e.status, 'PENDENTE')"
                ent_join = "LEFT JOIN entrega_atividade e ON e.id_atividade = a.id_atividade AND e.id_aluno = ?"
                ent_params = [c["idAluno"]]
            for a in rows(
                f"""SELECT a.id_atividade AS id, a.titulo, a.descricao, a.data_entrega, t.nome AS turma, d.nome AS disciplina,
                           {ent_sel} AS status
                      FROM atividade a JOIN turma_disciplina td ON td.id_turma_disciplina = a.id_turma_disciplina
                      JOIN turma t ON t.id_turma = td.id_turma JOIN disciplina d ON d.id_disciplina = td.id_disciplina
                      {ent_join}
                     WHERE {c['sql']} AND date(a.data_entrega) BETWEEN ? AND ?""",
                [*ent_params, *c["params"], ini.isoformat(), fi.isoformat()],
            ):
                saida.append({
                    "id": f"atividade-{a['id']}-{c['idAluno'] or 0}", "refId": a["id"], "tipo": "ATIVIDADE", "categoria": "ATIVIDADE",
                    "titulo": a["titulo"], "descricao": a["descricao"], "inicio": a["data_entrega"], "fim": None, "diaInteiro": False,
                    "turma": a["turma"], "disciplina": a["disciplina"], "status": a["status"] if c["idAluno"] else None,
                    "aluno": rotulo(c), "idAluno": c["idAluno"], "link": _LINKS["ATIVIDADE"],
                })

        if "AVALIACAO" in tipos:
            nota_sel, nota_join, nota_params = ("NULL", "", [])
            if c["idAluno"]:
                nota_sel, nota_join, nota_params = "n.valor", "LEFT JOIN nota n ON n.id_avaliacao = av.id_avaliacao AND n.id_aluno = ?", [c["idAluno"]]
            for av in rows(
                f"""SELECT av.id_avaliacao AS id, av.titulo, av.tipo, av.data_avaliacao, av.bimestre, t.nome AS turma, d.nome AS disciplina,
                           {nota_sel} AS nota
                      FROM avaliacao av JOIN turma_disciplina td ON td.id_turma_disciplina = av.id_turma_disciplina
                      JOIN turma t ON t.id_turma = td.id_turma JOIN disciplina d ON d.id_disciplina = td.id_disciplina
                      {nota_join}
                     WHERE {c['sql']} AND av.data_avaliacao BETWEEN ? AND ?""",
                [*nota_params, *c["params"], ini.isoformat(), fi.isoformat()],
            ):
                saida.append({
                    "id": f"avaliacao-{av['id']}-{c['idAluno'] or 0}", "refId": av["id"], "tipo": "AVALIACAO", "categoria": av["tipo"],
                    "titulo": f"{av['titulo']} — {av['disciplina']}", "inicio": av["data_avaliacao"], "fim": None, "diaInteiro": True,
                    "turma": av["turma"], "disciplina": av["disciplina"], "bimestre": av["bimestre"], "nota": av["nota"],
                    "aluno": rotulo(c), "idAluno": c["idAluno"], "link": _LINKS["AVALIACAO"],
                })

    if "EVENTO" in tipos:
        filtro, params = cm.filtro_comunicados(user)
        extra, ep = "", []
        if id_turma and user["perfil"] in ("COORDENADOR", "ADMIN", "PROFESSOR"):
            extra, ep = " AND (c.publico <> 'TURMA' OR c.id_turma = ?)", [id_turma]
        for e in rows(
            f"""SELECT c.id_evento AS id, c.titulo, c.descricao, c.inicio, c.fim, c.tipo, c.dia_inteiro, c.publico, t.nome AS turma
                  FROM evento c LEFT JOIN turma t ON t.id_turma = c.id_turma
                 WHERE {filtro} {extra} AND date(c.inicio) <= ? AND date(COALESCE(c.fim, c.inicio)) >= ?""",
            [*params, *ep, fi.isoformat(), ini.isoformat()],
        ):
            saida.append({
                "id": f"evento-{e['id']}", "refId": e["id"], "tipo": "EVENTO", "categoria": e["tipo"], "titulo": e["titulo"],
                "descricao": e["descricao"], "inicio": e["inicio"], "fim": e["fim"], "diaInteiro": bool(e["dia_inteiro"]),
                "turma": e["turma"], "publico": e["publico"], "aluno": None, "idAluno": None, "link": _LINKS["EVENTO"],
            })

    saida.sort(key=lambda i: (i["inicio"][:10], i["inicio"][11:16] if not i["diaInteiro"] and len(i["inicio"]) > 10 else "00:00", _ORDEM[i["tipo"]], i["titulo"]))
    return saida


def proximos(user: dict, dias: int = 14, limite: int = 6) -> list[dict]:
    """Próximos compromissos do usuário (dashboards): provas, entregas pendentes e eventos — sem as aulas.
    Entregas pendentes com prazo vencido hoje continuam aparecendo (são as mais urgentes)."""
    hoje = date.today()
    saida = []
    for i in itens(user, hoje.isoformat(), (hoje + timedelta(days=dias)).isoformat(), ["ATIVIDADE", "AVALIACAO", "EVENTO"]):
        if i["tipo"] == "ATIVIDADE" and i.get("status") in ("ENTREGUE", "CORRIGIDA"):
            continue
        saida.append({k: i.get(k) for k in ("id", "tipo", "categoria", "titulo", "inicio", "fim", "diaInteiro", "turma", "disciplina", "aluno", "status", "link")})
    return saida[:limite]


# ---------------------------------------------------------------------------
# Calendário de provas (PB16)
# ---------------------------------------------------------------------------
def provas(user: dict, id_aluno=None, id_turma=None, id_td=None, bimestre=None, periodo="proximas") -> list[dict]:
    from .acesso import pode_gerir_turma_disciplina

    hoje = date.today().isoformat()
    saida, vistos = [], set()
    ctxs = contextos(user, id_aluno, id_turma)
    multiplos = len({c["idAluno"] for c in ctxs}) > 1
    for c in ctxs:
        extra, ep = "", []
        if id_td:
            extra += " AND av.id_turma_disciplina = ?"
            ep.append(id_td)
        if bimestre:
            extra += " AND av.bimestre = ?"
            ep.append(bimestre)
        if periodo == "proximas":
            extra += " AND av.data_avaliacao >= ?"
            ep.append(hoje)
        elif periodo == "passadas":
            extra += " AND av.data_avaliacao < ?"
            ep.append(hoje)
        nota_sel, nota_join, np_ = ("NULL", "", [])
        if c["idAluno"]:
            nota_sel, nota_join, np_ = "n.valor", "LEFT JOIN nota n ON n.id_avaliacao = av.id_avaliacao AND n.id_aluno = ?", [c["idAluno"]]
        for av in rows(
            f"""SELECT av.id_avaliacao AS id, av.titulo, av.tipo, av.bimestre, av.peso, av.data_avaliacao AS data,
                       av.id_turma_disciplina AS idTurmaDisciplina, t.nome AS turma, d.nome AS disciplina, u.nome AS professor,
                       (SELECT COUNT(*) FROM nota x WHERE x.id_avaliacao = av.id_avaliacao) AS notasLancadas, {nota_sel} AS nota
                  FROM avaliacao av JOIN turma_disciplina td ON td.id_turma_disciplina = av.id_turma_disciplina
                  JOIN turma t ON t.id_turma = td.id_turma JOIN disciplina d ON d.id_disciplina = td.id_disciplina
                  LEFT JOIN usuario u ON u.id_usuario = td.id_professor
                  {nota_join}
                 WHERE {c['sql']} {extra}""",
            [*np_, *c["params"], *ep],
        ):
            chave = (av["id"], c["idAluno"])
            if chave in vistos:
                continue
            vistos.add(chave)
            av["diasRestantes"] = (date.fromisoformat(av["data"]) - date.fromisoformat(hoje)).days
            av["aluno"] = c["aluno"] if multiplos else None
            av["idAluno"] = c["idAluno"]
            av["podeRemarcar"] = pode_gerir_turma_disciplina(user, av["idTurmaDisciplina"]) and not av["notasLancadas"]
            saida.append(av)
    saida.sort(key=lambda a: (a["data"], a["turma"], a["disciplina"]), reverse=(periodo == "passadas"))
    return saida


# ---------------------------------------------------------------------------
# Notificações do módulo (integração com PB21)
# ---------------------------------------------------------------------------
def destinatarios_turma(id_turma: int) -> list[int]:
    """Alunos da turma e seus responsáveis (quem precisa saber de uma prova)."""
    return [r["id"] for r in rows(
        """SELECT id_aluno AS id FROM aluno WHERE id_turma = ?
           UNION SELECT ar.id_responsavel FROM aluno_responsavel ar JOIN aluno a ON a.id_aluno = ar.id_aluno WHERE a.id_turma = ?""",
        (id_turma, id_turma))]


def gerar_lembretes(user: dict) -> int:
    """Cria (uma única vez) lembretes de prova (até 2 dias) e de atividades pendentes que vencem em até 1 dia.
    Só para aluno e responsável. A chave única evita repetir o mesmo lembrete a cada consulta."""
    if user["perfil"] not in ("ALUNO", "RESPONSAVEL"):
        return 0
    hoje = date.today()
    novos = 0
    con = get_db()
    for i in itens(user, hoje.isoformat(), (hoje + timedelta(days=2)).isoformat(), ["ATIVIDADE", "AVALIACAO"]):
        quem = f" ({i['aluno']})" if i.get("aluno") else ""
        d = date.fromisoformat(i["inicio"][:10])
        if i["tipo"] == "AVALIACAO":
            falta = (d - hoje).days
            quando = "hoje" if falta == 0 else "amanhã" if falta == 1 else f"em {br(d)}"
            titulo, msg = f"Lembrete: avaliação {quando}{quem}", f"{i['titulo']} ({i['turma']}) é {quando}."
            chave = f"av:{i['refId']}:{i['idAluno']}:{d.isoformat()}"
        else:
            if i.get("status") in ("ENTREGUE", "CORRIGIDA") or datetime.fromisoformat(i["inicio"]) < datetime.now() or (d - hoje).days > 1:
                continue
            titulo, msg = f"Lembrete: atividade pendente{quem}", f"{i['titulo']} ({i['disciplina']}) vence em {br(d)} às {i['inicio'][11:16]}."
            chave = f"at:{i['refId']}:{i['idAluno']}:{d.isoformat()}"
        cur = con.execute(
            "INSERT INTO notificacao (id_usuario, tipo, titulo, mensagem, link, chave) VALUES (?,?,?,?,?,?) ON CONFLICT DO NOTHING",
            (user["id"], "AGENDA", titulo[:160], msg, i["link"], chave),
        )
        novos += cur.rowcount
    if novos:
        con.commit()
    return novos
