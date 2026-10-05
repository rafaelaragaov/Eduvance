"""Lançamento de notas (PB11): professor da turma, coordenador e administrador."""
from flask import Blueprint, current_app, g, jsonify, request

from ..db import execute, one, rows
from ..errors import ApiError, Corpo, nao_encontrado, proibido
from ..security import auth_required
from ..services.acesso import pode_gerir_turma_disciplina

bp = Blueprint("notas", __name__, url_prefix="/api/notas")


@bp.get("/turma-disciplina/<int:id_td>")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def da_turma(id_td):
    """Avaliação mais recente (preferindo o bimestre atual) e as notas dos alunos da turma."""
    if not pode_gerir_turma_disciplina(g.user, id_td):
        raise proibido()
    av = one(
        """SELECT id_avaliacao AS id, titulo, data_avaliacao AS data, bimestre
             FROM avaliacao WHERE id_turma_disciplina = ?
            ORDER BY (bimestre = ?) DESC, data_avaliacao DESC LIMIT 1""",
        (id_td, current_app.config["BIMESTRE_ATUAL"]),
    )
    if not av:
        return jsonify(avaliacao=None, alunos=[])
    alunos = rows(
        """SELECT a.id_aluno AS idAluno, u.nome, a.matricula, n.valor AS valor
             FROM turma_disciplina td
             JOIN aluno a ON a.id_turma = td.id_turma
             JOIN usuario u ON u.id_usuario = a.id_aluno
             LEFT JOIN nota n ON n.id_aluno = a.id_aluno AND n.id_avaliacao = ?
            WHERE td.id_turma_disciplina = ?
            ORDER BY a.matricula""",
        (av["id"], id_td),
    )
    return jsonify(avaliacao=av, alunos=alunos)


@bp.put("")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def lancar():
    """Cria/atualiza a nota de um aluno (valor nulo remove o lançamento)."""
    c = Corpo(request.get_json(silent=True))
    id_av = c.inteiro("idAvaliacao", "Avaliação")
    id_aluno = c.inteiro("idAluno", "Aluno")
    valor = None
    if c.d.get("valor") is not None and c.d.get("valor") != "":
        valor = c.numero("valor", "Nota", 0, 10)
    c.validar()

    av = one("SELECT id_turma_disciplina AS td FROM avaliacao WHERE id_avaliacao = ?", (id_av,))
    if not av:
        raise nao_encontrado("Avaliação")
    if not pode_gerir_turma_disciplina(g.user, av["td"]):
        raise proibido()
    if not one("SELECT 1 FROM aluno a JOIN turma_disciplina td ON td.id_turma = a.id_turma WHERE a.id_aluno = ? AND td.id_turma_disciplina = ?", (id_aluno, av["td"])):
        raise ApiError(400, "O aluno não pertence a esta turma")

    if valor is None:
        execute("DELETE FROM nota WHERE id_avaliacao = ? AND id_aluno = ?", (id_av, id_aluno))
    else:
        execute(
            """INSERT INTO nota (id_avaliacao, id_aluno, valor) VALUES (?,?,?)
               ON CONFLICT (id_avaliacao, id_aluno) DO UPDATE SET valor = excluded.valor""",
            (id_av, id_aluno, valor),
        )
    return jsonify(idAvaliacao=id_av, idAluno=id_aluno, valor=valor)
