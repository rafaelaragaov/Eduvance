"""Recomendações de estudo por aluno (Sprint 06) — consome o serviço de recomendação (FastAPI) ou o motor embutido."""
from flask import Blueprint, g, jsonify, request

from ..db import one
from ..errors import ApiError, nao_encontrado, proibido
from ..security import auth_required
from ..services import recomendacao as rec
from ..services.acesso import alunos_vinculados, pode_ver_aluno

bp = Blueprint("recomendacoes", __name__, url_prefix="/api/recomendacoes")


@bp.get("")
@auth_required()
def obter():
    """Aluno: as próprias. Responsável: de um filho (idAluno; se tiver só um, é opcional). Professor/coordenação/admin: idAluno."""
    u = g.user
    id_aluno = request.args.get("idAluno", type=int)
    if u["perfil"] == "ALUNO":
        if id_aluno and id_aluno != u["id"]:
            raise proibido("Você só pode ver as suas recomendações")
        id_aluno = u["id"]
    elif u["perfil"] == "RESPONSAVEL" and not id_aluno:
        filhos = alunos_vinculados(u["id"])
        if len(filhos) != 1:
            raise ApiError(400, "Informe o aluno (idAluno)")
        id_aluno = filhos[0]["id"]
    if not id_aluno:
        raise ApiError(400, "Informe o aluno (idAluno)")
    if not one("SELECT 1 FROM aluno WHERE id_aluno = ?", (id_aluno,)):
        raise nao_encontrado("Aluno")
    if not pode_ver_aluno(u, id_aluno):
        raise proibido("Você não tem permissão para ver as recomendações deste aluno")
    return jsonify(rec.gerar_e_salvar(id_aluno))
