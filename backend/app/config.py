"""Configurações da aplicação (podem ser sobrescritas por variáveis de ambiente)."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]  # raiz do repositório


class Config:
    # Banco de dados SQLite (o mesmo modelo entregue na Sprint 02)
    DATABASE = os.environ.get("EDUVANCE_DB", str(RAIZ / "database" / "eduvance.db"))
    SCHEMA_SQL = str(RAIZ / "database" / "schema.sql")

    # Autenticação
    JWT_SECRET = os.environ.get("EDUVANCE_JWT_SECRET", "dev-only-secret-change-me-please-32b!")
    JWT_HORAS = int(os.environ.get("EDUVANCE_JWT_HORAS", "8"))

    # Front-end compilado (servido pelo próprio Flask)
    FRONTEND_DIST = os.environ.get("EDUVANCE_FRONTEND", str(RAIZ / "frontend" / "dist"))

    # Regras de negócio
    LIMITE_FALTAS = 15
    META_FREQUENCIA = 90.0
    BIMESTRE_ATUAL = 2
    MEDIA_APROVACAO = 6.0
    FREQUENCIA_MINIMA = 75.0      # % mínima de presença exigida (Sprint 04)
    MIN_AULAS_PARA_FALTA = 10     # só aplica a reprovação por falta com pelo menos N aulas registradas

    # Proteção contra força bruta no login
    LOGIN_MAX_POR_MINUTO = int(os.environ.get("EDUVANCE_LOGIN_MAX", "20"))

    JSON_SORT_KEYS = False
    TESTING = False
