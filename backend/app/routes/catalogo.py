"""Listas auxiliares para os formulários (selects)."""
from flask import Blueprint, g, jsonify

from ..db import rows
from ..security import auth_required

bp = Blueprint("catalogo", __name__, url_prefix="/api/catalogo")


@bp.get("/turmas")
@auth_required()
def turmas():
    return jsonify(rows("SELECT id_turma AS id, nome, ano_letivo AS anoLetivo FROM turma ORDER BY nome"))


@bp.get("/disciplinas")
@auth_required()
def disciplinas():
    return jsonify(rows("SELECT id_disciplina AS id, nome FROM disciplina ORDER BY nome"))


@bp.get("/turma-disciplinas")
@auth_required()
def turma_disciplinas():
    """Professor: apenas as suas turmas/disciplinas. Coordenador/Admin: todas."""
    u = g.user
    if u["perfil"] in ("ALUNO", "RESPONSAVEL"):
        return jsonify([])
    filtro = "WHERE td.id_professor = ?" if u["perfil"] == "PROFESSOR" else ""
    return jsonify(rows(
        f"""SELECT td.id_turma_disciplina AS id, t.id_turma AS idTurma, t.nome AS turma,
                   d.nome AS disciplina, us.nome AS professor,
                   (SELECT COUNT(*) FROM aluno a WHERE a.id_turma = t.id_turma) AS alunos,
                   (SELECT COUNT(*) FROM nota n JOIN avaliacao av ON av.id_avaliacao = n.id_avaliacao
                     WHERE av.id_turma_disciplina = td.id_turma_disciplina) AS notasLancadas
              FROM turma_disciplina td
              JOIN turma t ON t.id_turma = td.id_turma
              JOIN disciplina d ON d.id_disciplina = td.id_disciplina
              LEFT JOIN usuario us ON us.id_usuario = td.id_professor
              {filtro}
             ORDER BY td.id_turma_disciplina""",
        (u["id"],) if filtro else (),
    ))
