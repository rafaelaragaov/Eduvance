"""Serviço HTTP de recomendação (FastAPI). Execução, a partir da raiz do repositório:

    pip install -r recomendacao/requirements.txt
    uvicorn recomendacao.servico:app --port 8001

O back-end Flask do Eduvance chama `POST /recomendar` quando a variável EDUVANCE_RECOMENDACAO_URL está definida
(ex.: http://127.0.0.1:8001). Sem ela, o Flask usa o mesmo motor de regras embutido.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from . import motor

app = FastAPI(title="Eduvance — Serviço de Recomendação", version="1.0.0",
              description="Cruza notas, frequência e agenda de provas para sugerir o que o aluno deve priorizar.")


class Nota(BaseModel):
    titulo: str = ""
    valor: Optional[float] = Field(None, ge=0, le=10)
    data: Optional[str] = None
    peso: float = 1


class Disciplina(BaseModel):
    nome: str = Field(..., min_length=1)
    media: Optional[float] = Field(None, ge=0, le=10)
    notas: list[Nota] = []
    frequencia: Optional[float] = Field(None, ge=0, le=100)
    aulas: int = Field(0, ge=0)
    faltas: int = Field(0, ge=0)


class Prova(BaseModel):
    titulo: str = ""
    disciplina: Optional[str] = None
    dias: int


class Atividade(BaseModel):
    titulo: str = ""
    disciplina: Optional[str] = None
    dias: int


class Dados(BaseModel):
    parametros: dict[str, Any] = {}
    disciplinas: list[Disciplina] = []
    faltas: int = Field(0, ge=0)
    provas: list[Prova] = []
    atividades: list[Atividade] = []


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "servico": "recomendacao", "versao": app.version}


@app.post("/recomendar")
def recomendar(dados: Dados) -> dict[str, Any]:
    return motor.gerar(dados.model_dump())
