"""Motor de recomendação do Eduvance — regras explicáveis, sem dependências externas.

Cruza três fontes que vivem em módulos diferentes do sistema:
  * Notas e Boletim (média por disciplina, tendência das últimas avaliações);
  * Frequência (faltas e percentual de presença);
  * Agenda (provas marcadas e entregas de atividades que vencem em breve).

A entrada é um dicionário simples (o mesmo JSON que o serviço FastAPI recebe) e a saída é uma lista de
recomendações ordenadas por prioridade. Cada item traz o `motivo` (os números que o originaram), para que o
aluno e o responsável entendam o porquê da sugestão — não há "caixa-preta".
"""
from __future__ import annotations

from typing import Any

PADROES = {"mediaAprovacao": 6.0, "limiteFaltas": 15, "frequenciaMinima": 75.0, "minAulasParaFalta": 5}
LIMITE_ITENS = 6
JANELA_PROVA_DIAS = 7

ROTULO_PRIORIDADE = {"ALTA": "Alta", "MEDIA": "Média", "BAIXA": "Baixa"}


def _prioridade(score: float) -> str:
    return "ALTA" if score >= 70 else "MEDIA" if score >= 40 else "BAIXA"


def _fmt(n: float | None) -> str:
    return "—" if n is None else f"{n:.1f}".replace(".", ",")


def _dias(n: int) -> str:
    return "hoje" if n == 0 else "amanhã" if n == 1 else f"em {n} dias"


def _item(tipo: str, score: float, titulo: str, mensagem: str, motivo: dict[str, Any], disciplina: str | None = None, link: str = "/") -> dict:
    score = max(0.0, min(100.0, round(score, 1)))
    return {
        "tipo": tipo, "prioridade": _prioridade(score), "score": score, "titulo": titulo,
        "mensagem": mensagem, "disciplina": disciplina, "motivo": motivo, "link": link,
    }


def _tendencia(notas: list[dict]) -> float | None:
    """Diferença entre a última nota e a média das anteriores (negativo = queda). Precisa de ao menos 3 notas."""
    valores = [n["valor"] for n in sorted(notas, key=lambda n: n.get("data") or "") if n.get("valor") is not None]
    if len(valores) < 3:
        return None
    return valores[-1] - sum(valores[:-1]) / len(valores[:-1])


def gerar(dados: dict[str, Any]) -> dict[str, Any]:
    """Gera as recomendações de um aluno. Nunca lança por dado ausente: campos faltantes assumem padrões."""
    par = {**PADROES, **(dados.get("parametros") or {})}
    aprov = float(par["mediaAprovacao"])
    disciplinas = dados.get("disciplinas") or []
    por_nome = {d["nome"]: d for d in disciplinas}
    itens: list[dict] = []

    # 1) Reforço por desempenho (Notas)
    for d in disciplinas:
        media, nome = d.get("media"), d["nome"]
        if media is not None and media < aprov:
            falta = aprov - media
            itens.append(_item(
                "REFORCO", 60 + falta * 8, f"Reforço em {nome}",
                f"Sua média em {nome} está em {_fmt(media)} — faltam {_fmt(falta)} ponto(s) para a média {_fmt(aprov)}. "
                "Revise os conteúdos já avaliados e procure o professor para tirar dúvidas.",
                {"media": media, "mediaAprovacao": aprov}, nome, "/boletim"))
        elif media is not None and media < aprov + 1:
            itens.append(_item(
                "REFORCO", 40, f"Atenção em {nome}",
                f"Sua média em {nome} é {_fmt(media)}, pouco acima do mínimo ({_fmt(aprov)}). Uma nota ruim na próxima avaliação pode colocá-la em risco.",
                {"media": media, "mediaAprovacao": aprov}, nome, "/boletim"))
        queda = _tendencia(d.get("notas") or [])
        if queda is not None and queda <= -1.5:
            itens.append(_item(
                "REFORCO", 35 + abs(queda) * 3, f"Notas em queda em {nome}",
                f"A última nota de {nome} ficou {_fmt(abs(queda))} ponto(s) abaixo das anteriores. Vale entender o que mudou.",
                {"queda": round(queda, 2)}, nome, "/boletim"))
        if media is not None and media >= 9:
            itens.append(_item(
                "DESTAQUE", 20, f"Ótimo desempenho em {nome}",
                f"Média {_fmt(media)} em {nome}. Que tal treinar com os simulados da Área de Vestibular?",
                {"media": media}, nome, "/vestibular"))

    # 2) Provas próximas × desempenho (Agenda × Notas)
    for p in sorted(dados.get("provas") or [], key=lambda x: x.get("dias", 99)):
        dias = int(p.get("dias", 99))
        if dias < 0 or dias > JANELA_PROVA_DIAS:
            continue
        d = por_nome.get(p.get("disciplina"))
        media = d.get("media") if d else None
        score = 50 + (JANELA_PROVA_DIAS + 1 - dias) * 5
        if media is not None and media < aprov:
            score += 20
        elif media is not None and media < aprov + 1:
            score += 10
        minutos = 60 if media is not None and media < aprov else 45 if media is not None and media < aprov + 1 else 30
        plano = f"Sugestão: {minutos} min por dia de estudo até a data."
        contexto = f" Sua média atual na disciplina é {_fmt(media)}." if media is not None else ""
        itens.append(_item(
            "PROVA", score, f"{p.get('titulo', 'Avaliação')} {_dias(dias)}",
            f"{p.get('titulo', 'Avaliação')} de {p.get('disciplina', 'disciplina')} {_dias(dias)}.{contexto} {plano}",
            {"dias": dias, "media": media, "minutosPorDia": minutos}, p.get("disciplina"), "/provas"))

    # 3) Frequência (Frequência)
    faltas, limite = int(dados.get("faltas") or 0), int(par["limiteFaltas"])
    razao = faltas / limite if limite else 0
    if razao >= 1:
        itens.append(_item("FREQUENCIA", 100, "Limite de faltas atingido",
                           f"Você tem {faltas} falta(s) — o limite é {limite}. Converse com a coordenação sobre a justificativa.",
                           {"faltas": faltas, "limite": limite}, None, "/boletim"))
    elif razao >= 0.8:
        itens.append(_item("FREQUENCIA", 75, "Faltas perto do limite",
                           f"Você já tem {faltas} de {limite} faltas permitidas. Evite novas ausências.",
                           {"faltas": faltas, "limite": limite}, None, "/boletim"))
    elif razao >= 0.6:
        itens.append(_item("FREQUENCIA", 45, "Fique de olho nas faltas",
                           f"{faltas} de {limite} faltas permitidas já foram usadas.", {"faltas": faltas, "limite": limite}, None, "/boletim"))
    for d in disciplinas:
        freq, aulas = d.get("frequencia"), int(d.get("aulas") or 0)
        if freq is not None and aulas >= int(par["minAulasParaFalta"]) and freq < float(par["frequenciaMinima"]):
            itens.append(_item("FREQUENCIA", 85, f"Frequência baixa em {d['nome']}",
                               f"Presença de {freq:.0f}% em {d['nome']}; o mínimo exigido é {par['frequenciaMinima']:.0f}%.",
                               {"frequencia": freq, "minimo": par["frequenciaMinima"]}, d["nome"], "/boletim"))

    # 4) Entregas (Atividades × Agenda)
    for a in dados.get("atividades") or []:
        dias = int(a.get("dias", 99))
        if dias > 1:
            continue
        atrasada = dias < 0
        itens.append(_item(
            "ATIVIDADE", 65 if atrasada else 55, f"{'Entrega atrasada' if atrasada else 'Entrega ' + _dias(dias)}: {a.get('titulo', 'atividade')}",
            f"{a.get('titulo', 'Atividade')} ({a.get('disciplina', '')}) "
            + ("está com o prazo vencido. Entregue o quanto antes e avise o professor." if atrasada else f"vence {_dias(dias)}."),
            {"dias": dias}, a.get("disciplina"), "/atividades"))

    # 5) Ordena, remove duplicadas de mesmo título e limita
    vistos: set[tuple[str, str]] = set()
    unicos = []
    for i in sorted(itens, key=lambda x: (-x["score"], x["titulo"])):
        chave = (i["tipo"], i["titulo"])
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(i)
    unicos = unicos[:LIMITE_ITENS]
    altas = sum(1 for i in unicos if i["prioridade"] == "ALTA")
    nivel = "ATENCAO" if altas >= 2 else "CUIDADO" if altas == 1 else "TRANQUILO"
    return {"itens": unicos, "resumo": {"nivel": nivel, "altas": altas, "total": len(unicos)}}
