"""Recomendações de estudo (Sprint 06) — integra Notas, Frequência e Agenda e consulta o serviço de recomendação.

Fluxo: coleta os dados do aluno nos outros módulos -> chama o serviço FastAPI (EDUVANCE_RECOMENDACAO_URL) ->
se o serviço não responder (ou não estiver configurado), usa o MESMO motor de regras embutido -> grava o
resultado em `recomendacao_ia` (histórico do que foi sugerido) -> devolve ao front-end com a origem indicada.
"""
import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime

from flask import current_app

from ..config import RAIZ
from ..db import rows, transacao
from . import academico as ac
from . import agenda as ag

if str(RAIZ) not in sys.path:  # o pacote `recomendacao/` fica na raiz do repositório
    sys.path.insert(0, str(RAIZ))
from recomendacao import motor  # noqa: E402


def coletar(id_aluno: int) -> dict:
    """Reúne, em um único documento, o que o motor precisa saber do aluno."""
    cfg = current_app.config
    bol = ac.boletim_completo(id_aluno)
    b_atual = str(bol["bimestreAtual"])
    disciplinas = []
    for d in bol["disciplinas"]:
        media = d["bimestres"].get(b_atual)
        if media is None:
            media = d["mediaParcial"]
        disciplinas.append({
            "nome": d["materia"], "media": media, "frequencia": d["frequencia"], "aulas": d["aulas"], "faltas": d["faltas"],
            "notas": [{"titulo": a["titulo"], "valor": a["nota"], "data": a["data"], "peso": a["peso"]} for a in d["avaliacoes"] if a["nota"] is not None],
        })
    hoje = date.today()
    provas = [{"titulo": p["titulo"], "disciplina": p["disciplina"], "dias": p["diasRestantes"]}
              for p in ag.provas({"perfil": "ALUNO", "id": id_aluno}, periodo="proximas")]
    atividades = []
    for a in rows(
        """SELECT at.titulo, at.data_entrega AS dataEntrega, d.nome AS disciplina
             FROM aluno al
             JOIN turma_disciplina td ON td.id_turma = al.id_turma
             JOIN disciplina d ON d.id_disciplina = td.id_disciplina
             JOIN atividade at ON at.id_turma_disciplina = td.id_turma_disciplina
             LEFT JOIN entrega_atividade ea ON ea.id_atividade = at.id_atividade AND ea.id_aluno = al.id_aluno
            WHERE al.id_aluno = ? AND COALESCE(ea.status, 'PENDENTE') = 'PENDENTE'
            ORDER BY at.data_entrega""",
        (id_aluno,),
    ):
        prazo = datetime.fromisoformat(a["dataEntrega"].replace(" ", "T")).date()
        atividades.append({"titulo": a["titulo"], "disciplina": a["disciplina"], "dias": (prazo - hoje).days})
    return {
        "parametros": {"mediaAprovacao": cfg["MEDIA_APROVACAO"], "limiteFaltas": cfg["LIMITE_FALTAS"],
                       "frequenciaMinima": cfg["FREQUENCIA_MINIMA"], "minAulasParaFalta": cfg["MIN_AULAS_PARA_FALTA"]},
        "disciplinas": disciplinas, "faltas": bol["faltasTotal"], "provas": provas, "atividades": atividades,
    }


def _chamar_servico(url: str, dados: dict, timeout: float) -> dict:
    req = urllib.request.Request(f"{url}/recomendar", data=json.dumps(dados).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 — URL vem da configuração do servidor
        saida = json.loads(r.read().decode())
    if not isinstance(saida, dict) or not isinstance(saida.get("itens"), list):
        raise ValueError("resposta fora do contrato")
    return saida


def consultar(dados: dict) -> tuple[dict, str]:
    """Devolve (resultado, origem). origem: 'servico' | 'motor' | 'motor-fallback'."""
    cfg = current_app.config
    url = cfg.get("RECOMENDACAO_URL")
    if not url:
        return motor.gerar(dados), "motor"
    try:
        return _chamar_servico(url, dados, cfg["RECOMENDACAO_TIMEOUT"]), "servico"
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as e:
        current_app.logger.warning("Serviço de recomendação indisponível (%s); usando o motor embutido.", e)
        return motor.gerar(dados), "motor-fallback"


def gerar_e_salvar(id_aluno: int) -> dict:
    dados = coletar(id_aluno)
    resultado, origem = consultar(dados)
    disc = {r["nome"]: r["id"] for r in rows("SELECT id_disciplina AS id, nome FROM disciplina")}
    with transacao() as con:
        con.execute("DELETE FROM recomendacao_ia WHERE id_aluno = ?", (id_aluno,))
        for i in resultado["itens"]:
            con.execute(
                """INSERT INTO recomendacao_ia (id_aluno, id_disciplina, tipo, prioridade, score, titulo, justificativa, motivo, link, origem)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (id_aluno, disc.get(i.get("disciplina")), i["tipo"], i["prioridade"], i["score"], i["titulo"], i["mensagem"],
                 json.dumps(i.get("motivo") or {}, ensure_ascii=False), i.get("link"), "servico" if origem == "servico" else "motor"),
            )
    return {"idAluno": id_aluno, "origem": origem, "geradaEm": datetime.now().isoformat(timespec="seconds"), **resultado}
