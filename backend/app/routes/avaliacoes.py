"""Avaliações (provas, trabalhos, testes e projetos) — PB11/PB16, módulo Notas, Frequência e Boletim (Sprint 04).

 - PROFESSOR: gerencia as avaliações das turmas/disciplinas em que leciona.
 - COORDENADOR e ADMIN: gerenciam todas.
"""
from flask import Blueprint, g, jsonify, request

from ..db import execute, one, rows
from ..errors import ApiError, Corpo, nao_encontrado, proibido
from ..security import auth_required
from ..services.acesso import pode_gerir_turma_disciplina

bp = Blueprint("avaliacoes", __name__, url_prefix="/api/avaliacoes")

TIPOS = ["PROVA", "TRABALHO", "TESTE", "PROJETO"]

_BASE = """
  SELECT av.id_avaliacao AS id, av.titulo, av.tipo, av.bimestre, av.data_avaliacao AS dataAvaliacao, av.peso,
         av.id_turma_disciplina AS idTurmaDisciplina, t.nome AS turma, t.ano_letivo AS anoLetivo, d.nome AS disciplina,
         (SELECT COUNT(*) FROM nota n WHERE n.id_avaliacao = av.id_avaliacao) AS notasLancadas,
         (SELECT COUNT(*) FROM aluno a WHERE a.id_turma = td.id_turma) AS totalAlunos,
         (SELECT ROUND(AVG(n.valor), 1) FROM nota n WHERE n.id_avaliacao = av.id_avaliacao) AS mediaTurma
    FROM avaliacao av
    JOIN turma_disciplina td ON td.id_turma_disciplina = av.id_turma_disciplina
    JOIN turma t ON t.id_turma = td.id_turma
    JOIN disciplina d ON d.id_disciplina = td.id_disciplina"""


def _por_id(id_: int) -> dict | None:
    return one(_BASE + " WHERE av.id_avaliacao = ?", (id_,))


def _corpo(id_atual: int | None = None) -> dict:
    c = Corpo(request.get_json(silent=True))
    d = {
        "titulo": c.texto("titulo", "Título", minimo=3, maximo=120),
        "tipo": c.opcao("tipo", "Tipo", TIPOS),
        "bimestre": c.inteiro("bimestre", "Bimestre"),
        "dataAvaliacao": c.data("dataAvaliacao", "Data da avaliação"),
        "peso": c.numero("peso", "Peso", 0.5, 5, obrigatorio=False),
        "idTurmaDisciplina": c.inteiro("idTurmaDisciplina", "Turma/disciplina"),
    }
    if d["bimestre"] is not None and not 1 <= d["bimestre"] <= 4:
        c._erro("bimestre", "Bimestre deve estar entre 1 e 4")
    if d["peso"] is None:
        d["peso"] = 1.0
    c.validar()

    td = one(
        """SELECT t.ano_letivo AS ano FROM turma_disciplina td JOIN turma t ON t.id_turma = td.id_turma
            WHERE td.id_turma_disciplina = ?""",
        (d["idTurmaDisciplina"],),
    )
    if not td:
        raise ApiError(400, "Turma/disciplina inválida", [{"campo": "idTurmaDisciplina", "mensagem": "Turma/disciplina inexistente"}])
    if int(d["dataAvaliacao"][:4]) != td["ano"]:
        raise ApiError(400, "Dados inválidos", [{"campo": "dataAvaliacao", "mensagem": f"A data deve estar dentro do ano letivo da turma ({td['ano']})"}])
    dup = one(
        """SELECT id_avaliacao FROM avaliacao
            WHERE id_turma_disciplina = ? AND bimestre = ? AND lower(titulo) = lower(?) AND id_avaliacao <> COALESCE(?, 0)""",
        (d["idTurmaDisciplina"], d["bimestre"], d["titulo"], id_atual),
    )
    if dup:
        raise ApiError(409, "Já existe uma avaliação com este título neste bimestre para a turma/disciplina",
                       [{"campo": "titulo", "mensagem": "Já existe uma avaliação com este título neste bimestre"}])
    return d


@bp.get("")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def listar():
    where, params = [], []
    if g.user["perfil"] == "PROFESSOR":
        where.append("td.id_professor = ?")
        params.append(g.user["id"])
    td = request.args.get("idTurmaDisciplina", type=int)
    if td:
        where.append("av.id_turma_disciplina = ?")
        params.append(td)
    bim = request.args.get("bimestre", type=int)
    if bim:
        where.append("av.bimestre = ?")
        params.append(bim)
    sql = _BASE + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY av.data_avaliacao DESC, av.id_avaliacao DESC"
    return jsonify(rows(sql, params))


@bp.get("/<int:id_>")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def obter(id_):
    a = _por_id(id_)
    if not a:
        raise nao_encontrado("Avaliação", feminino=True)
    if not pode_gerir_turma_disciplina(g.user, a["idTurmaDisciplina"]):
        raise proibido()
    return jsonify(a)


@bp.post("")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def criar():
    d = _corpo()
    if not pode_gerir_turma_disciplina(g.user, d["idTurmaDisciplina"]):
        raise proibido("Você não leciona esta disciplina nesta turma")
    novo = execute(
        "INSERT INTO avaliacao (id_turma_disciplina, titulo, tipo, bimestre, data_avaliacao, peso) VALUES (?,?,?,?,?,?)",
        (d["idTurmaDisciplina"], d["titulo"], d["tipo"], d["bimestre"], d["dataAvaliacao"], d["peso"]),
    )
    return jsonify(_por_id(novo)), 201


@bp.put("/<int:id_>")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def atualizar(id_):
    atual = _por_id(id_)
    if not atual:
        raise nao_encontrado("Avaliação", feminino=True)
    if not pode_gerir_turma_disciplina(g.user, atual["idTurmaDisciplina"]):
        raise proibido()
    d = _corpo(id_)
    if not pode_gerir_turma_disciplina(g.user, d["idTurmaDisciplina"]):
        raise proibido("Você não leciona esta disciplina nesta turma")
    if atual["notasLancadas"] and d["idTurmaDisciplina"] != atual["idTurmaDisciplina"]:
        raise ApiError(409, "Não é possível mudar a turma/disciplina de uma avaliação que já possui notas lançadas")
    execute(
        """UPDATE avaliacao SET id_turma_disciplina = ?, titulo = ?, tipo = ?, bimestre = ?, data_avaliacao = ?, peso = ?
            WHERE id_avaliacao = ?""",
        (d["idTurmaDisciplina"], d["titulo"], d["tipo"], d["bimestre"], d["dataAvaliacao"], d["peso"], id_),
    )
    return jsonify(_por_id(id_))


@bp.delete("/<int:id_>")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def excluir(id_):
    atual = _por_id(id_)
    if not atual:
        raise nao_encontrado("Avaliação", feminino=True)
    if not pode_gerir_turma_disciplina(g.user, atual["idTurmaDisciplina"]):
        raise proibido()
    if atual["notasLancadas"]:
        raise ApiError(409, f"Não é possível excluir: já existem {atual['notasLancadas']} notas lançadas nesta avaliação. "
                            "Remova as notas antes de excluir.")
    execute("DELETE FROM avaliacao WHERE id_avaliacao = ?", (id_,))
    return "", 204
