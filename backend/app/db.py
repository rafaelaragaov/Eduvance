"""Acesso ao banco de dados: SQLite (padrão, sem instalação) ou PostgreSQL 16 (Sprint 06 — migração real).

A escolha é feita só por configuração:
    EDUVANCE_DATABASE_URL=postgresql://usuario:senha@host:5432/eduvance   -> PostgreSQL
    (sem a variável)  EDUVANCE_DB=caminho/do/arquivo.db                    -> SQLite

O restante da aplicação continua escrevendo SQL com o marcador `?` e lendo as linhas por nome ou posição. No
PostgreSQL, `ConexaoPG` faz a ponte: troca `?` por `%s`, traduz as poucas expressões próprias do SQLite
(`datetime('now','localtime')`, `date('now','localtime')`, `group_concat`, `LIKE` -> `ILIKE`), devolve as colunas
com a caixa original dos apelidos (o PostgreSQL passaria tudo para minúsculas), converte NUMERIC/DATE/TIMESTAMP/TIME
para os mesmos tipos Python que o SQLite entrega (float/str) e informa `lastrowid` via RETURNING.
"""
from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time
from decimal import Decimal

from flask import current_app, g

try:  # psycopg 3 só é necessário quando EDUVANCE_DATABASE_URL aponta para o PostgreSQL
    import psycopg
    from psycopg import errors as pg_errors
except ImportError:  # pragma: no cover - ambiente só com SQLite
    psycopg = None
    pg_errors = None

URL_PG = ("postgresql://", "postgres://")


def eh_postgres(destino: str | None) -> bool:
    return bool(destino) and str(destino).startswith(URL_PG)


def banco_configurado() -> str:
    """Destino do banco da aplicação atual: URL do PostgreSQL ou caminho do arquivo SQLite."""
    return current_app.config.get("DATABASE_URL") or current_app.config["DATABASE"]


def dialeto() -> str:
    return "postgresql" if eh_postgres(banco_configurado()) else "sqlite"


# ---------------------------------------------------------------------------
# Tradução SQLite -> PostgreSQL
# ---------------------------------------------------------------------------
_TRADUCOES = [
    (re.compile(r"datetime\(\s*'now'\s*,\s*'localtime'\s*,\s*\?\s*\)", re.I), "(localtimestamp(0) + CAST(? AS interval))"),
    (re.compile(r"datetime\(\s*'now'\s*,\s*'localtime'\s*\)", re.I), "localtimestamp(0)"),
    (re.compile(r"date\(\s*'now'\s*,\s*'localtime'\s*\)", re.I), "current_date"),
    (re.compile(r"\?\s+IS\s+(NOT\s+)?NULL", re.I), lambda m: f"CAST(? AS TEXT) IS {m.group(1) or ''}NULL"),   # tipo do parâmetro
    (re.compile(r"\bIS\s+NOT\s+\?", re.I), "IS DISTINCT FROM ?"),
    (re.compile(r"\bIS\s+\?", re.I), "IS NOT DISTINCT FROM ?"),
    (re.compile(r"\bgroup_concat\(", re.I), "string_agg("),
    (re.compile(r"\bLIKE\b", re.I), "ILIKE"),
]
_ALIAS = re.compile(r"\bAS\s+([A-Za-z_]\w*)", re.I)
_INSERT = re.compile(r"^\s*INSERT\s+INTO\s+([A-Za-z_]\w*)", re.I)


def traduzir_para_pg(sql: str) -> str:
    """Converte o SQL escrito para SQLite no dialeto do PostgreSQL (somente o que o Eduvance usa)."""
    for rx, novo in _TRADUCOES:
        sql = rx.sub(novo, sql)
    return sql.replace("%", "%%").replace("?", "%s")


def _valor(v):
    """Tipos do PostgreSQL -> os mesmos que o SQLite devolve (a aplicação trata datas como texto ISO)."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat(timespec="seconds")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, time):
        return v.strftime("%H:%M") if v.second == 0 else v.strftime("%H:%M:%S")
    if isinstance(v, bool):
        return int(v)
    return v


class Linha(dict):
    """Linha de resultado: acesso por nome (r['nome']) ou por posição (r[0]), como sqlite3.Row."""

    def __getitem__(self, chave):
        if isinstance(chave, int):
            return list(self.values())[chave]
        return super().__getitem__(chave)


class CursorPG:
    def __init__(self, cur, mapa_alias: dict[str, str], lastrowid=None):
        self._cur, self._mapa, self.lastrowid = cur, mapa_alias, lastrowid
        self.rowcount = cur.rowcount
        self._nomes = [self._mapa.get(c.name, c.name) for c in (cur.description or [])]

    def _linha(self, r) -> Linha:
        return Linha(zip(self._nomes, (_valor(v) for v in r)))

    def fetchone(self):
        r = self._cur.fetchone()
        return None if r is None else self._linha(r)

    def fetchall(self):
        return [self._linha(r) for r in self._cur.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


class ConexaoPG:
    """Fachada com a mesma interface usada da conexão sqlite3: execute / executemany / executescript / commit."""

    def __init__(self, url: str, schema: str | None = None):
        if psycopg is None:
            raise RuntimeError("Para usar o PostgreSQL instale o driver: pip install \"psycopg[binary]\"")
        opcoes = {"options": f"-c search_path={schema}"} if schema else {}
        self._con = psycopg.connect(url, **opcoes)
        self._pks: dict[str, str | None] = {}

    def _pk_unica(self, tabela: str) -> str | None:
        if tabela not in self._pks:
            r = self._con.execute(
                """SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = to_regclass(%s) AND i.indisprimary""", (tabela,)).fetchall()
            self._pks[tabela] = r[0][0] if len(r) == 1 else None
        return self._pks[tabela]

    def execute(self, sql: str, params=()) -> CursorPG:
        alias = {m.lower(): m for m in _ALIAS.findall(sql) if m != m.lower()}
        novo = traduzir_para_pg(sql)
        pk = None
        m = _INSERT.match(sql)
        if m and "RETURNING" not in sql.upper():
            pk = self._pk_unica(m.group(1))
            if pk:
                novo = novo.rstrip().rstrip(";") + f" RETURNING {pk}"
        cur = self._con.cursor()
        cur.execute(novo, tuple(params))
        ultimo = None
        if pk:
            r = cur.fetchone()
            ultimo = r[0] if r else None
            cur = _SemLinhas(cur)
        return CursorPG(cur, alias, ultimo)

    def executemany(self, sql: str, lote) -> CursorPG:
        cur = self._con.cursor()
        cur.executemany(traduzir_para_pg(sql), [tuple(p) for p in lote])
        return CursorPG(cur, {})

    def executescript(self, sql: str) -> None:
        self._con.execute(sql)  # várias instruções, sem parâmetros
        self._con.commit()

    def commit(self):
        self._con.commit()

    def rollback(self):
        self._con.rollback()

    def close(self):
        self._con.close()


class _SemLinhas:
    """Cursor depois do RETURNING consumido: sem linhas e sem descrição."""
    description = None

    def __init__(self, cur):
        self.rowcount = cur.rowcount

    def fetchone(self):
        return None

    def fetchall(self):
        return []


# ---------------------------------------------------------------------------
# Conexão por requisição + atalhos usados em toda a aplicação
# ---------------------------------------------------------------------------
def conectar(destino: str, schema: str | None = None):
    """Abre a conexão: arquivo SQLite (com integridade referencial) ou URL do PostgreSQL."""
    if eh_postgres(destino):
        return ConexaoPG(destino, schema)
    con = sqlite3.connect(destino, timeout=15)  # com várias threads atendendo, espera o outro terminar de gravar em vez de falhar
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def get_db():
    if "db" not in g:
        cfg = current_app.config
        g.db = conectar(cfg.get("DATABASE_URL") or cfg["DATABASE"], cfg.get("DATABASE_SCHEMA"))
    return g.db


def fechar_db(_exc=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def erros_de_integridade() -> tuple[type, ...]:
    return (sqlite3.IntegrityError,) + ((psycopg.errors.IntegrityError,) if psycopg else ())


def mensagem_integridade(e: Exception) -> str:
    """Texto do erro de integridade no formato do SQLite ("UNIQUE constraint failed: tabela.coluna", "FOREIGN KEY ...").
    Para o PostgreSQL ele é reconstruído a partir do SQLSTATE e do diagnóstico, assim o tratamento de erros da API é um só."""
    if psycopg is None or not isinstance(e, psycopg.errors.IntegrityError):
        return str(e)
    d = e.diag
    if isinstance(e, pg_errors.UniqueViolation):
        colunas = re.findall(r"[A-Za-z_]\w*", (re.match(r"Key \((.*?)\)=", d.message_detail or "") or [None, ""])[1])
        colunas = [c for c in colunas if c.lower() not in ("lower", "upper")]
        return "UNIQUE constraint failed: " + ", ".join(f"{d.table_name}.{c}" for c in colunas)
    if isinstance(e, pg_errors.ForeignKeyViolation):
        return "FOREIGN KEY constraint failed"
    return d.message_primary or str(e)


def rows(sql: str, params=()) -> list[dict]:
    return [dict(r) for r in get_db().execute(sql, params).fetchall()]


def one(sql: str, params=()) -> dict | None:
    r = get_db().execute(sql, params).fetchone()
    return dict(r) if r else None


def scalar(sql: str, params=()):
    r = get_db().execute(sql, params).fetchone()
    return r[0] if r else None


def execute(sql: str, params=()) -> int:
    """Executa um comando de escrita e confirma. Retorna o id gerado (lastrowid)."""
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
