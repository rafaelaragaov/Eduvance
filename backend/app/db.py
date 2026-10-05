"""Acesso ao banco SQLite: uma conexão por requisição, com integridade referencial ativa."""
import sqlite3
from contextlib import contextmanager

from flask import current_app, g


def conectar(caminho: str) -> sqlite3.Connection:
    con = sqlite3.connect(caminho)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = conectar(current_app.config["DATABASE"])
    return g.db


def fechar_db(_exc=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def rows(sql: str, params=()) -> list[dict]:
    return [dict(r) for r in get_db().execute(sql, params).fetchall()]


def one(sql: str, params=()) -> dict | None:
    r = get_db().execute(sql, params).fetchone()
    return dict(r) if r else None


def scalar(sql: str, params=()):
    r = get_db().execute(sql, params).fetchone()
    return r[0] if r else None


def execute(sql: str, params=()) -> int:
    """Executa um comando de escrita e confirma. Retorna lastrowid."""
    con = get_db()
    cur = con.execute(sql, params)
    con.commit()
    return cur.lastrowid


@contextmanager
def transacao():
    """Agrupa várias escritas numa única transação (commit/rollback automáticos)."""
    con = get_db()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
