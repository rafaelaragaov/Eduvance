"""Paralelismo (Sprint 07): recálculo das recomendações de todos os alunos e teste de carga multiprocessador.

Por que processos e não threads: em Python só uma thread executa código Python por vez dentro de um processo
(o "GIL"), mesmo compilado. Para ocupar todos os processadores com cálculo é preciso um processo por thread
lógica. A API web continua com threads (esperar banco/rede libera o GIL); o cálculo pesado usa processos.

Dois usos, ambos a partir do executável (ver `eduvance.py`):

  * recalcular_todos()  — trabalho real: lê os dados de cada aluno (processo principal), calcula as recomendações
                          em paralelo (motor de regras) e grava o resultado de volta em `recomendacao_ia`.
  * benchmark()         — carga de teste: repete o cálculo do motor até todos os processadores ficarem ocupados
                          por `segundos` e mede tempo, vazão, ganho sobre 1 processo e uso de CPU.
"""
from __future__ import annotations

import math
import os
import random
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from datetime import date
from typing import Callable

from .config import RAIZ

if str(RAIZ) not in sys.path:  # o pacote `recomendacao/` fica na raiz do projeto
    sys.path.insert(0, str(RAIZ))
from recomendacao import motor  # noqa: E402

TAREFA_SEGUNDOS = 0.5  # duração-alvo de cada tarefa enviada aos processos (curta o bastante para não sobrar processador ocioso no fim)


def resolver_processos(valor: str | int | None) -> int:
    """'auto' (ou vazio) = uma tarefa por thread lógica do processador; senão, o número pedido."""
    if valor in (None, "", "auto"):
        return os.cpu_count() or 1
    n = int(valor)
    if n < 1:
        raise ValueError("o número de processos deve ser pelo menos 1")
    return n


# ---------------------------------------------------------------------------
# Código executado dentro de cada processo
# ---------------------------------------------------------------------------
_LOTE: list[dict] = []


def _iniciar(lote: list[dict]) -> None:
    """Roda uma vez por processo: guarda os dados em memória (assim cada tarefa envia só um número)."""
    global _LOTE
    _LOTE = lote


def _executar(repeticoes: int) -> tuple[int, float, float]:
    """Calcula as recomendações de todo o lote `repeticoes` vezes. Devolve (cálculos, soma dos scores, segundos de CPU)."""
    cpu0 = time.process_time()
    chamadas, soma = 0, 0.0
    for _ in range(repeticoes):
        for dados in _LOTE:
            saida = motor.gerar(dados)
            soma += sum(i["score"] for i in saida["itens"])
            chamadas += 1
    return chamadas, soma, time.process_time() - cpu0


def _dormir(segundos: float) -> int:
    time.sleep(segundos)
    return os.getpid()


def _gerar(dados: dict) -> dict:
    return motor.gerar(dados)


# ---------------------------------------------------------------------------
# Dados de entrada
# ---------------------------------------------------------------------------
def lote_sintetico(n: int = 60, semente: int = 7) -> list[dict]:
    """Alunos fictícios, sempre os mesmos para a mesma semente (usado quando não há banco)."""
    rnd = random.Random(semente)
    nomes = ["Matemática", "Português", "História", "Ciências", "Geografia", "Inglês"]
    lote = []
    for a in range(n):
        disciplinas = []
        for nome in nomes:
            notas = [{"titulo": f"Avaliação {k + 1}", "valor": round(rnd.uniform(3, 10), 1), "data": f"2026-0{3 + k}-1{k + 1}", "peso": 1.0}
                     for k in range(rnd.randint(3, 5))]
            media = round(sum(x["valor"] for x in notas) / len(notas), 1)
            aulas = rnd.randint(20, 40)
            faltas = rnd.randint(0, 12)
            disciplinas.append({"nome": nome, "media": media, "frequencia": round(100 * (aulas - faltas) / aulas, 1),
                                "aulas": aulas, "faltas": faltas, "notas": notas})
        lote.append({
            "parametros": {"mediaAprovacao": 6.0, "limiteFaltas": 15, "frequenciaMinima": 75.0, "minAulasParaFalta": 10},
            "disciplinas": disciplinas, "faltas": sum(d["faltas"] for d in disciplinas),
            "provas": [{"titulo": f"Prova {k}", "disciplina": rnd.choice(nomes), "dias": rnd.randint(0, 10)} for k in range(rnd.randint(0, 3))],
            "atividades": [{"titulo": f"Atividade {k}", "disciplina": rnd.choice(nomes), "dias": rnd.randint(-2, 6)} for k in range(rnd.randint(0, 3))],
        })
    return lote


def lote_do_banco(app=None) -> list[dict]:
    """Dados reais de todos os alunos do banco configurado (leitura no processo principal)."""
    from . import create_app
    from .db import rows
    from .services import recomendacao as rec

    app = app or create_app()
    with app.app_context():
        ids = [r["id"] for r in rows("SELECT id_aluno AS id FROM aluno ORDER BY id_aluno")]
        return [rec.coletar(i) for i in ids]


# ---------------------------------------------------------------------------
# 1) Trabalho real: recalcular as recomendações de todos os alunos
# ---------------------------------------------------------------------------
def recalcular_todos(processos: int, saida: Callable[[str], None] = print, app=None) -> dict:
    from . import create_app
    from .db import rows
    from .services import recomendacao as rec

    app = app or create_app()
    with app.app_context():
        t0 = time.perf_counter()
        ids = [r["id"] for r in rows("SELECT id_aluno AS id FROM aluno ORDER BY id_aluno")]
        dados = [rec.coletar(i) for i in ids]
        t_leitura = time.perf_counter() - t0

        t1 = time.perf_counter()
        if processos == 1:
            resultados = [_gerar(d) for d in dados]
        else:
            with ProcessPoolExecutor(max_workers=processos) as pool:
                resultados = list(pool.map(_gerar, dados, chunksize=max(1, math.ceil(len(dados) / (processos * 4)))))
        t_calculo = time.perf_counter() - t1

        t2 = time.perf_counter()
        for id_aluno, r in zip(ids, resultados):
            rec.salvar(id_aluno, r, "motor")
        t_gravacao = time.perf_counter() - t2

    itens = sum(len(r["itens"]) for r in resultados)
    res = {"alunos": len(ids), "processos": processos, "itens": itens, "leitura": t_leitura, "calculo": t_calculo,
           "gravacao": t_gravacao, "total": time.perf_counter() - t0}
    saida(f"Alunos processados ...... {res['alunos']}")
    saida(f"Processos de cálculo .... {processos}")
    saida(f"Recomendações geradas ... {itens} (gravadas em recomendacao_ia)")
    saida(f"Leitura do banco ........ {t_leitura:.3f} s (processo principal)")
    saida(f"Cálculo em paralelo ..... {t_calculo:.3f} s")
    saida(f"Gravação no banco ....... {t_gravacao:.3f} s (processo principal)")
    saida(f"Total ................... {res['total']:.3f} s")
    saida("Obs.: com poucos alunos o cálculo leva milissegundos e o custo de criar processos domina;")
    saida("      o ganho de verdade aparece na carga de teste (--benchmark-paralelo).")
    return res


# ---------------------------------------------------------------------------
# 2) Carga de teste: todos os processadores ocupados
# ---------------------------------------------------------------------------
def _taxa_sequencial(lote: list[dict], janela: float = 2.0) -> tuple[float, float]:
    """Cálculos por segundo em UM processo (processo principal) e a soma de referência de uma volta do lote."""
    _iniciar(lote)
    referencia = _executar(1)[1]
    t0 = time.perf_counter()
    chamadas = 0
    while time.perf_counter() - t0 < janela:
        chamadas += _executar(1)[0]
    return chamadas / (time.perf_counter() - t0), referencia


def benchmark(processos: int, segundos: float, lote: list[dict] | None = None, saida: Callable[[str], None] = print,
              janela: float = 2.0, app=None) -> dict:
    origem = "dados reais do banco"
    if lote is None:
        try:
            lote = lote_do_banco(app)
        except Exception:  # sem banco / sem tabelas: usa alunos fictícios
            lote, origem = [], ""
        if not lote:
            lote, origem = lote_sintetico(), "alunos fictícios (sem banco)"
    else:
        origem = "lote informado"

    saida(f"Processadores (threads lógicas) detectados: {os.cpu_count()}")
    saida(f"Processos usados no teste: {processos} · duração alvo: {segundos:g} s · carga: {len(lote)} alunos ({origem})")
    saida("")
    saida(f"1/2  Medindo a velocidade de UM processo ({janela:g} s)...")
    taxa1, ref_volta = _taxa_sequencial(lote, janela)
    saida(f"     1 processo faz {taxa1:,.0f} cálculos/s".replace(",", "."))

    repeticoes = max(1, round(taxa1 * TAREFA_SEGUNDOS / len(lote)))
    saida("")
    saida(f"2/2  Rodando com {processos} processo(s) por ~{segundos:g} s (tarefas de ~{TAREFA_SEGUNDOS:g} s). Abra o Gerenciador de Tarefas > Desempenho.")
    with ProcessPoolExecutor(max_workers=processos, initializer=_iniciar, initargs=(lote,)) as pool:
        for f in [pool.submit(_dormir, 0.4) for _ in range(processos)]:  # força todos os processos a subirem antes de medir
            f.result()
        t0 = time.perf_counter()
        fim = t0 + segundos
        em_andamento = {pool.submit(_executar, repeticoes) for _ in range(processos * 2)}  # fila sempre cheia: nenhum processo fica ocioso
        n_tarefas, proximo = len(em_andamento), t0 + 1
        resultados = []
        while em_andamento:
            prontos, em_andamento = wait(em_andamento, return_when=FIRST_COMPLETED)
            for f in prontos:
                resultados.append(f.result())
                if time.perf_counter() < fim:  # repõe a fila até o tempo acabar (a duração não depende do ganho obtido)
                    em_andamento.add(pool.submit(_executar, repeticoes))
                    n_tarefas += 1
            if time.perf_counter() >= proximo:
                saida(f"     {time.perf_counter() - t0:5.1f} s · {len(resultados)} tarefas concluídas")
                proximo += 1
        duracao = time.perf_counter() - t0

    chamadas = sum(r[0] for r in resultados)
    cpu = sum(r[2] for r in resultados)
    taxa_n = chamadas / duracao
    ganho = taxa_n / taxa1
    uso = 100 * cpu / (duracao * processos)
    somas = {round(r[1] / (r[0] / len(lote)), 6) for r in resultados}  # soma por volta do lote: tem de ser igual em todas as tarefas
    consistente = somas == {round(ref_volta, 6)}

    res = {"processos": processos, "cpus": os.cpu_count(), "duracao": duracao, "chamadas": chamadas, "taxa_1": taxa1, "taxa_n": taxa_n,
           "ganho": ganho, "eficiencia": 100 * ganho / processos, "uso_cpu": uso, "consistente": consistente, "tarefas": n_tarefas}
    saida("")
    saida("================  RESULTADO  ================")
    saida(f"Processos ................ {processos} (processadores lógicos: {os.cpu_count()})")
    saida(f"Duração .................. {duracao:.2f} s")
    saida(f"Cálculos realizados ...... {chamadas:,}".replace(",", "."))
    saida(f"Vazão com 1 processo ..... {taxa1:,.0f} cálculos/s".replace(",", "."))
    saida(f"Vazão com {processos} processo(s) ... {taxa_n:,.0f} cálculos/s".replace(",", "."))
    saida(f"Ganho (speedup) .......... {ganho:.2f}x   (ideal: {processos}x)")
    saida(f"Eficiência ............... {100 * ganho / processos:.0f}%")
    saida(f"Uso médio de CPU ......... {uso:.0f}%  (tempo de CPU dos processos / tempo decorrido x processos)")
    saida(f"Resultado idêntico ao sequencial: {'sim' if consistente else 'NÃO - verificar'}")
    saida(f"Data/hora: {date.today().isoformat()} {time.strftime('%H:%M:%S')}")
    return res
