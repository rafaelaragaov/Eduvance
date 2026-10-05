"""Área de Vestibular (PB23, PB25, PB28, PB29) - exibida ao aluno."""
from flask import Blueprint, g, jsonify, request

from ..db import execute, rows
from ..errors import Corpo
from ..security import auth_required

bp = Blueprint("vestibular", __name__, url_prefix="/api/vestibular")

FOCOS = ["ENEM", "Unicamp", "FUVEST"]


def _classifica(p: float) -> str:
    if p >= 700:
        return "Excelente"
    if p >= 600:
        return "Acima da Média"
    if p >= 450:
        return "Regular"
    return "Abaixo da Média"


@bp.get("")
@auth_required("ALUNO")
def painel():
    id_ = g.user["id"]
    foco = request.args.get("foco")
    foco = foco if foco in FOCOS else None

    simulados = rows(
        """SELECT s.id_simulado AS id, s.titulo, s.data_aplicacao AS data, s.vestibular, r.pontuacao
             FROM resultado_simulado r JOIN simulado s ON s.id_simulado = r.id_simulado
            WHERE r.id_aluno = ? AND (? IS NULL OR s.vestibular = ?)
            ORDER BY s.data_aplicacao DESC LIMIT 5""",
        (id_, foco, foco),
    )
    for s in simulados:
        s["classificacao"] = _classifica(s["pontuacao"])

    return jsonify(
        focos=FOCOS,
        foco=foco,
        simulados=simulados,
        redacoes=rows(
            """SELECT r.id_redacao AS id, r.tema, r.status, r.nota, u.nome AS avaliador, r.enviada_em AS enviadaEm
                 FROM redacao r LEFT JOIN usuario u ON u.id_usuario = r.id_professor
                WHERE r.id_aluno = ? ORDER BY r.enviada_em DESC LIMIT 5""",
            (id_,),
        ),
        foruns=rows(
            """SELECT f.id_forum AS id, f.titulo, d.nome AS disciplina,
                      (SELECT COUNT(*) FROM post_forum p WHERE p.id_forum = f.id_forum) AS respostas
                 FROM forum f LEFT JOIN disciplina d ON d.id_disciplina = f.id_disciplina
                ORDER BY f.data_criacao DESC LIMIT 5"""
        ),
        materiais=rows(
            """SELECT id_material AS id, titulo, tipo, detalhe, url FROM material
                WHERE (? IS NULL OR vestibular IS NULL OR vestibular = ?) ORDER BY id_material LIMIT 6""",
            (foco, foco),
        ),
    )


@bp.post("/redacoes")
@auth_required("ALUNO")
def enviar_redacao():
    c = Corpo(request.get_json(silent=True))
    tema = c.texto("tema", "Tema", minimo=5, maximo=200)
    texto = c.texto("texto", "Texto", minimo=50, maximo=10000)
    c.validar()
    novo = execute("INSERT INTO redacao (id_aluno, tema, texto) VALUES (?,?,?)", (g.user["id"], tema, texto))
    return jsonify(id=novo, tema=tema, status="ENVIADA"), 201
