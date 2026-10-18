"""Migra os dados de um banco SQLite do Eduvance para o PostgreSQL (Sprint 06).

    export EDUVANCE_DATABASE_URL=postgresql://eduvance:eduvance@localhost:5432/eduvance
    python -m app.migrar_para_postgres                     # lê o SQLite de EDUVANCE_DB (padrão: database/eduvance.db)
    python -m app.migrar_para_postgres --sqlite outro.db --reset

O que faz: cria o schema `schema.postgresql.sql` (com --reset recria do zero), copia as tabelas na ordem das chaves
estrangeiras, converte os tipos (texto ISO -> DATE/TIMESTAMP/TIME, 0/1 -> SMALLINT), acerta as sequências (SERIAL)
para que os próximos cadastros não repitam ids e confere as contagens de linhas de cada tabela.
"""
import argparse
import os
import re
import sqlite3
import sys

from .config import Config
from .db import ConexaoPG, eh_postgres


def ordem_das_tabelas(origem: sqlite3.Connection) -> list[str]:
    tabelas = [r[0] for r in origem.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    deps = {t: {r[2] for r in origem.execute(f"PRAGMA foreign_key_list({t})") if r[2] != t} for t in tabelas}
    ordem: list[str] = []
    while len(ordem) < len(tabelas):
        prontos = [t for t in tabelas if t not in ordem and deps[t] <= set(ordem)]
        if not prontos:
            raise RuntimeError(f"Dependência circular entre tabelas: {set(tabelas) - set(ordem)}")
        ordem += prontos
    return ordem


def migrar(sqlite_path: str, url: str, schema: str = "", reset: bool = False) -> dict[str, int]:
    from .init_db import criar_banco
    if not os.path.isfile(sqlite_path):
        raise FileNotFoundError(f"SQLite não encontrado: {sqlite_path}")
    criar_banco(url, reset=reset, com_dados=False, schema=schema)
    origem = sqlite3.connect(sqlite_path)
    destino = ConexaoPG(url, schema or None)
    contagens: dict[str, int] = {}
    try:
        for tabela in ordem_das_tabelas(origem):
            colunas_pg = {r["column_name"] for r in destino.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = ?", (tabela,)).fetchall()}
            cur = origem.execute(f"SELECT * FROM {tabela}")
            nomes = [d[0] for d in cur.description]
            usar = [n for n in nomes if n in colunas_pg]
            ignoradas = set(nomes) - set(usar)
            if ignoradas:
                print(f"  ! {tabela}: colunas fora do schema PostgreSQL ignoradas: {sorted(ignoradas)}")
            linhas = [tuple(l[nomes.index(n)] for n in usar) for l in cur.fetchall()]
            if linhas:
                destino.executemany(f"INSERT INTO {tabela} ({', '.join(usar)}) VALUES ({', '.join('?' * len(usar))})", linhas)
            contagens[tabela] = len(linhas)
        destino.commit()
        # sequências: próximo id = maior id + 1
        for r in destino.execute(
            """SELECT c.table_name AS t, c.column_name AS c FROM information_schema.columns c
                WHERE c.table_schema = current_schema() AND c.column_default LIKE 'nextval(%'""").fetchall():
            destino.execute(
                f"SELECT setval(pg_get_serial_sequence('{r['t']}', '{r['c']}'), COALESCE(MAX({r['c']}), 1), MAX({r['c']}) IS NOT NULL) FROM {r['t']}")
        destino.commit()
        # conferência
        for tabela, n in contagens.items():
            no_pg = destino.execute(f"SELECT COUNT(*) AS n FROM {tabela}").fetchone()["n"]
            if no_pg != n:
                raise RuntimeError(f"Tabela {tabela}: {n} linhas no SQLite, {no_pg} no PostgreSQL")
    finally:
        origem.close()
        destino.close()
    return contagens


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sqlite", default=Config.DATABASE)
    ap.add_argument("--url", default=Config.DATABASE_URL)
    ap.add_argument("--schema", default=Config.DATABASE_SCHEMA)
    ap.add_argument("--reset", action="store_true", help="recria o schema do PostgreSQL antes de copiar")
    a = ap.parse_args()
    if not eh_postgres(a.url):
        print("Informe o destino: --url postgresql://... ou EDUVANCE_DATABASE_URL", file=sys.stderr)
        return 2
    c = migrar(a.sqlite, a.url, a.schema, a.reset)
    print(f"✔ Migração concluída: {len(c)} tabelas, {sum(c.values())} linhas conferidas.")
    for t, n in c.items():
        print(f"  {t:24} {n:>6}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
