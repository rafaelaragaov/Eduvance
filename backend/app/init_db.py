"""Cria o banco (SQLite ou PostgreSQL) a partir do schema e insere os dados de demonstração.

    python -m app.init_db            # cria (se não existir) e popula
    python -m app.init_db --reset    # apaga e recria tudo

Banco de destino: PostgreSQL se EDUVANCE_DATABASE_URL estiver definida; senão, o arquivo SQLite de EDUVANCE_DB.
"""
import os
import re
import sqlite3
import sys

from .config import Config
from .db import ConexaoPG, conectar, eh_postgres
from .seed import SENHA_ADMIN, SENHA_PADRAO, popular


def criar_banco(destino: str | None = None, reset: bool = False, com_dados: bool = True, schema: str | None = None) -> str:
    """Cria e popula o banco. `destino` é um caminho SQLite ou uma URL postgresql://. Retorna o destino usado."""
    destino = destino or Config.DATABASE_URL or Config.DATABASE
    if eh_postgres(destino):
        return _criar_postgres(destino, reset, com_dados, schema if schema is not None else Config.DATABASE_SCHEMA)
    os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
    if reset and os.path.exists(destino):
        os.remove(destino)
    if os.path.exists(destino):
        con = sqlite3.connect(destino)
        n = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'usuario'").fetchone()[0]
        con.close()
        if n:
            print(f"• Banco já existe em {destino} (use --reset para recriar)")
            return destino

    con = conectar(destino)
    try:
        with open(Config.SCHEMA_SQL, encoding="utf-8") as f:
            con.executescript(f.read())
        print(f"• Tabelas criadas a partir de {os.path.basename(Config.SCHEMA_SQL)}")
        if com_dados:
            popular(con)
            print("• Dados de demonstração inseridos")
        con.commit()
    finally:
        con.close()
    return destino


def _criar_postgres(url: str, reset: bool, com_dados: bool, schema: str) -> str:
    if schema and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema):
        raise ValueError("Nome de schema inválido")
    admin = ConexaoPG(url)
    try:
        alvo = schema or "public"
        if reset:
            admin.execute(f"DROP SCHEMA IF EXISTS {alvo} CASCADE")
            admin.execute(f"CREATE SCHEMA {alvo}")
            admin.commit()
        elif schema:
            admin.execute(f"CREATE SCHEMA IF NOT EXISTS {alvo}")
            admin.commit()
    finally:
        admin.close()
    con = ConexaoPG(url, schema or None)
    try:
        if con.execute("SELECT to_regclass('usuario') AS t").fetchone()["t"]:
            print(f"• Banco PostgreSQL já possui as tabelas (use --reset para recriar)")
            return url
        with open(Config.SCHEMA_PG_SQL, encoding="utf-8") as f:
            con.executescript(f.read())
        print(f"• Tabelas criadas a partir de {os.path.basename(Config.SCHEMA_PG_SQL)} (PostgreSQL)")
        if com_dados:
            popular(con)
            print("• Dados de demonstração inseridos")
        con.commit()
    finally:
        con.close()
    return url


if __name__ == "__main__":
    destino = criar_banco(reset="--reset" in sys.argv)
    from datetime import date

    print(f"\n✔ Banco pronto: {'PostgreSQL' if eh_postgres(destino) else destino}\nContas de demonstração:")
    print(f"  Admin         admin@eduvance.com   / {SENHA_ADMIN}")
    print(f"  Coordenadora  paula@eduvance.com   / {SENHA_PADRAO}")
    print(f"  Professor     ricardo@eduvance.com / {SENHA_PADRAO}")
    print(f"  Aluno         matrícula {date.today().year}0001 (Lucas)  / {SENHA_PADRAO}")
    print(f"  Responsável   maria@eduvance.com   / {SENHA_PADRAO}")
