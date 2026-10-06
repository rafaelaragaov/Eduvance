"""Boletim completo do aluno (PB10) — notas por bimestre, média, frequência e situação."""
from flask import Blueprint, g, jsonify

from ..db import one
from ..errors import nao_encontrado, proibido
from ..security import auth_required
from ..services.academico import boletim_completo
from ..services.acesso import pode_ver_aluno

bp = Blueprint("boletim", __name__, url_prefix="/api/boletim")


@bp.get("/<int:id_aluno>")
@auth_required()
def obter(id_aluno):
    """Aluno vê o próprio; responsável, só o dos vinculados; professor, os das suas turmas; coordenação/admin, todos."""
    if not one("SELECT 1 FROM aluno WHERE id_aluno = ?", (id_aluno,)):
        raise nao_encontrado("Aluno")
    if not pode_ver_aluno(g.user, id_aluno):
        raise proibido("Você não tem permissão para ver o boletim deste aluno")
    return jsonify(boletim_completo(id_aluno))
