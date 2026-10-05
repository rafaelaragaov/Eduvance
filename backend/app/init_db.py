"""Cria o banco SQLite a partir de database/schema.sql e insere os dados de demonstração.

    python -m app.init_db            # cria (se não existir) e popula
    python -m app.init_db --reset    # apaga e recria tudo
"""
import os
import sqlite3
import sys

from .config import Config
from .db import conectar
from .seed import SENHA_ADMIN, SENHA_PADRAO, popular


def criar_banco(caminho: str | None = None, reset: bool = False, com_dados: bool = True) -> str:
    caminho = caminho or Config.DATABASE
    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
    if reset and os.path.exists(caminho):
        os.remove(caminho)
    if os.path.exists(caminho):
        con = sqlite3.connect(caminho)
        n = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'usuario'").fetchone()[0]
        con.close()
        if n:
            print(f"• Banco já existe em {caminho} (use --reset para recriar)")
            return caminho

    con = conectar(caminho)
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
    return caminho


if __name__ == "__main__":
    caminho = criar_banco(reset="--reset" in sys.argv)
    from datetime import date

    print(f"\n✔ Banco pronto: {caminho}\nContas de demonstração:")
    print(f"  Admin         admin@eduvance.com   / {SENHA_ADMIN}")
    print(f"  Coordenadora  paula@eduvance.com   / {SENHA_PADRAO}")
    print(f"  Professor     ricardo@eduvance.com / {SENHA_PADRAO}")
    print(f"  Aluno         matrícula {date.today().year}0001 (Lucas)  / {SENHA_PADRAO}")
    print(f"  Responsável   maria@eduvance.com   / {SENHA_PADRAO}")
