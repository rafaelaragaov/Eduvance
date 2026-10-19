"""Eduvance — ponto de entrada único: serve o sistema, cria o banco e roda os modos paralelos.

Funciona como código-fonte (`python eduvance.py ...`) e como executável compilado pelo Nuitka (`eduvance.exe ...`,
gerado por `compilar.bat`). Exemplos:

    eduvance.exe                                         # sobe o sistema em http://localhost:5000
    eduvance.exe --init-db [--reset]                     # cria (ou recria) o banco com os dados de demonstração
    eduvance.exe --benchmark-paralelo --processos auto   # carga de teste: todos os processadores a 100%
    eduvance.exe --recalcular-recomendacoes --processos auto
    eduvance.exe --benchmark-paralelo --relatorio resultado.txt   # também grava o resultado em arquivo
"""
import argparse
import multiprocessing
import os
import sys


def _utf8() -> None:
    """Console e arquivos de log em UTF-8 (no Windows, a saída redirecionada usaria a página de código local)."""
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _argumentos(argv):
    ap = argparse.ArgumentParser(prog="eduvance", description="Eduvance — sistema de gestão e acompanhamento educacional.")
    modo = ap.add_argument_group("o que fazer (sem nenhuma opção, sobe o sistema)")
    modo.add_argument("--init-db", action="store_true", help="cria o banco com os dados de demonstração (use --reset para recriar)")
    modo.add_argument("--benchmark-paralelo", action="store_true", help="carga de teste que ocupa todos os processadores e mede o ganho")
    modo.add_argument("--recalcular-recomendacoes", action="store_true", help="recalcula, em paralelo, as recomendações de todos os alunos")
    modo.add_argument("--versao", action="store_true", help="mostra a versão e o modo de execução")
    ap.add_argument("--reset", action="store_true", help="com --init-db: apaga e recria o banco")
    ap.add_argument("--processos", default="auto", help="processos de cálculo: um número ou 'auto' (= threads lógicas do processador)")
    ap.add_argument("--segundos", type=float, default=20.0, help="duração alvo da carga de teste (padrão: 20)")
    ap.add_argument("--relatorio", metavar="ARQUIVO", help="também grava em arquivo (UTF-8) o que os modos paralelos imprimem")
    ap.add_argument("--porta", type=int, default=int(os.environ.get("PORT", "5000")))
    ap.add_argument("--threads", type=int, default=int(os.environ.get("EDUVANCE_THREADS", "0")),
                    help="threads que atendem as requisições (padrão: 4 por processador lógico, no máximo 32)")
    return ap.parse_args(argv)


def _saida(arquivo):
    """Função que imprime na tela e, se pedido, acrescenta a linha em um arquivo (evidência para o relatório)."""
    if not arquivo:
        return print
    os.makedirs(os.path.dirname(os.path.abspath(arquivo)), exist_ok=True)
    open(arquivo, "w", encoding="utf-8").close()

    def escrever(linha: str) -> None:
        print(linha, flush=True)
        with open(arquivo, "a", encoding="utf-8") as f:
            f.write(linha + "\n")

    return escrever


def _servir(porta: int, threads: int) -> int:
    from app import create_app
    from app.config import Config
    from app.db import eh_postgres
    from app.init_db import criar_banco

    destino = Config.DATABASE_URL or Config.DATABASE
    if not eh_postgres(destino) and not os.path.isfile(destino):
        print("• Banco não encontrado: criando com os dados de demonstração...")
        criar_banco()
    threads = threads or min(32, (os.cpu_count() or 2) * 4)
    app = create_app()
    print(f"OK  Eduvance em http://localhost:{porta}  (banco: {destino})")
    try:
        from waitress import serve  # servidor de produção com várias threads

        print(f"    servidor: waitress · {threads} threads de atendimento · Ctrl+C para parar")
        serve(app, host="127.0.0.1", port=porta, threads=threads)
    except ImportError:
        print("    servidor: Flask/Werkzeug (modo threaded) · instale 'waitress' para o servidor de produção")
        app.run(host="127.0.0.1", port=porta, threaded=True)
    return 0


def main(argv=None) -> int:
    _utf8()
    a = _argumentos(argv)

    if a.versao:
        from app.config import COMPILADO, RAIZ

        print(f"Eduvance · execução: {'executável compilado (Nuitka)' if COMPILADO else 'código-fonte Python'} · "
              f"Python {sys.version.split()[0]} · pasta do projeto: {RAIZ} · processadores lógicos: {os.cpu_count()}")
        return 0
    if a.init_db:
        from app.init_db import criar_banco

        criar_banco(reset=a.reset)
        return 0
    if a.benchmark_paralelo or a.recalcular_recomendacoes:
        from app import paralelo

        try:
            n = paralelo.resolver_processos(a.processos)
        except ValueError as e:
            print(f"Erro: {e}", file=sys.stderr)
            return 2
        if a.benchmark_paralelo:
            r = paralelo.benchmark(n, a.segundos, saida=_saida(a.relatorio))
            return 0 if r["consistente"] else 1
        paralelo.recalcular_todos(n, saida=_saida(a.relatorio))
        return 0
    return _servir(a.porta, a.threads)


if __name__ == "__main__":
    multiprocessing.freeze_support()  # obrigatório no Windows para os processos filhos de um executável compilado
    sys.exit(main())
