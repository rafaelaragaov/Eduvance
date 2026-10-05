"""CRUD principal do sistema: ATIVIDADES (PB14 / PB15).

 - PROFESSOR: cadastra, consulta, atualiza e exclui atividades das suas turmas.
 - COORDENADOR e ADMIN: gerenciam todas.
 - ALUNO: consulta as da sua turma e marca a entrega.
 - RESPONSAVEL: consulta (somente leitura) as do aluno vinculado.
"""
from flask import Blueprint, g, jsonify, request

from ..db import execute, one, rows
from ..errors import ApiError, Corpo, nao_encontrado, proibido
from ..security import auth_required
from ..services.academico import urgencia
from ..services.acesso import alunos_vinculados, pode_gerir_turma_disciplina, pode_ver_aluno

bp = Blueprint("atividades", __name__, url_prefix="/api/atividades")

_BASE = """
  SELECT at.id_atividade AS id, at.titulo, at.descricao, at.data_entrega AS dataEntrega,
         at.id_turma_disciplina AS idTurmaDisciplina, t.nome AS turma, d.nome AS disciplina,
         up.nome AS professor, td.id_professor AS idProfessor{extra}
    FROM atividade at
    JOIN turma_disciplina td ON td.id_turma_disciplina = at.id_turma_disciplina
    JOIN turma t ON t.id_turma = td.id_turma
    JOIN disciplina d ON d.id_disciplina = td.id_disciplina
    LEFT JOIN usuario up ON up.id_usuario = td.id_professor"""


def _corpo():
    c = Corpo(request.get_json(silent=True))
    d = {
        "titulo": c.texto("titulo", "Título", minimo=3, maximo=160),
        "descricao": c.texto("descricao", "Descrição", maximo=2000, obrigatorio=False),
        "dataEntrega": c.data_hora("dataEntrega", "Prazo"),
        "idTurmaDisciplina": c.inteiro("idTurmaDisciplina", "Turma/disciplina"),
    }
    c.validar()
    return d


def _por_id(id_: int) -> dict | None:
    return one(_BASE.format(extra="") + " WHERE at.id_atividade = ?", (id_,))


@bp.get("")
@auth_required()
def listar():
    u = g.user
    if u["perfil"] in ("ALUNO", "RESPONSAVEL"):
        id_aluno = u["id"]
        if u["perfil"] == "RESPONSAVEL":
            vinc = alunos_vinculados(u["id"])
            pedido = request.args.get("alunoId", type=int)
            id_aluno = pedido or (vinc[0]["id"] if vinc else None)
            if not id_aluno or not pode_ver_aluno(u, id_aluno):
                return jsonify([])
        linhas = rows(
            _BASE.format(extra=", COALESCE(ea.status,'PENDENTE') AS statusEntrega")
            + """ JOIN aluno al ON al.id_turma = td.id_turma AND al.id_aluno = ?
                  LEFT JOIN entrega_atividade ea ON ea.id_atividade = at.id_atividade AND ea.id_aluno = al.id_aluno
                 ORDER BY at.data_entrega""",
            (id_aluno,),
        )
    else:
        extra = """,
          (SELECT COUNT(*) FROM entrega_atividade e WHERE e.id_atividade = at.id_atividade AND e.status <> 'PENDENTE') AS entregues,
          (SELECT COUNT(*) FROM aluno x WHERE x.id_turma = td.id_turma) AS total"""
        filtro, params = ("WHERE td.id_professor = ?", (u["id"],)) if u["perfil"] == "PROFESSOR" else ("", ())
        linhas = rows(_BASE.format(extra=extra) + f" {filtro} ORDER BY at.data_entrega DESC", params)

    for l in linhas:
        l["urgencia"] = urgencia(l["dataEntrega"], l.get("statusEntrega", "PENDENTE"))
    return jsonify(linhas)


@bp.get("/<int:id_>")
@auth_required()
def obter(id_):
    a = _por_id(id_)
    if not a:
        raise nao_encontrado("Atividade")
    u = g.user
    if u["perfil"] == "PROFESSOR" and a["idProfessor"] != u["id"]:
        raise proibido()
    if u["perfil"] == "ALUNO":
        ok = one("""SELECT 1 FROM aluno a JOIN turma_disciplina td ON td.id_turma = a.id_turma
                     WHERE a.id_aluno = ? AND td.id_turma_disciplina = ?""", (u["id"], a["idTurmaDisciplina"]))
        if not ok:
            raise proibido()
    if u["perfil"] == "RESPONSAVEL":
        ok = one("""SELECT 1 FROM aluno_responsavel ar JOIN aluno a ON a.id_aluno = ar.id_aluno
                      JOIN turma_disciplina td ON td.id_turma = a.id_turma
                     WHERE ar.id_responsavel = ? AND td.id_turma_disciplina = ?""", (u["id"], a["idTurmaDisciplina"]))
        if not ok:
            raise proibido()
    return jsonify(a)


@bp.post("")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def criar():
    d = _corpo()
    if not one("SELECT 1 FROM turma_disciplina WHERE id_turma_disciplina = ?", (d["idTurmaDisciplina"],)):
        raise ApiError(400, "Turma/disciplina inválida")
    if not pode_gerir_turma_disciplina(g.user, d["idTurmaDisciplina"]):
        raise proibido("Você não leciona esta disciplina nesta turma")
    novo = execute(
        "INSERT INTO atividade (id_turma_disciplina, titulo, descricao, data_entrega) VALUES (?,?,?,?)",
        (d["idTurmaDisciplina"], d["titulo"], d["descricao"], d["dataEntrega"]),
    )
    return jsonify(_por_id(novo)), 201


@bp.put("/<int:id_>")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def atualizar(id_):
    atual = one("SELECT id_turma_disciplina AS td FROM atividade WHERE id_atividade = ?", (id_,))
    if not atual:
        raise nao_encontrado("Atividade")
    d = _corpo()
    if not one("SELECT 1 FROM turma_disciplina WHERE id_turma_disciplina = ?", (d["idTurmaDisciplina"],)):
        raise ApiError(400, "Turma/disciplina inválida")
    if not (pode_gerir_turma_disciplina(g.user, atual["td"]) and pode_gerir_turma_disciplina(g.user, d["idTurmaDisciplina"])):
        raise proibido("Você não leciona esta disciplina nesta turma")
    execute(
        "UPDATE atividade SET id_turma_disciplina = ?, titulo = ?, descricao = ?, data_entrega = ? WHERE id_atividade = ?",
        (d["idTurmaDisciplina"], d["titulo"], d["descricao"], d["dataEntrega"], id_),
    )
    return jsonify(_por_id(id_))


@bp.delete("/<int:id_>")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def excluir(id_):
    atual = one("SELECT id_turma_disciplina AS td FROM atividade WHERE id_atividade = ?", (id_,))
    if not atual:
        raise nao_encontrado("Atividade")
    if not pode_gerir_turma_disciplina(g.user, atual["td"]):
        raise proibido()
    execute("DELETE FROM atividade WHERE id_atividade = ?", (id_,))
    return "", 204


@bp.put("/<int:id_>/entrega")
@auth_required("ALUNO")
def entrega(id_):
    """Aluno marca/desmarca a entrega da atividade (PB15 - controle de status)."""
    c = Corpo(request.get_json(silent=True))
    status = c.texto("status", "Status")
    if status not in ("ENTREGUE", "PENDENTE"):
        c._erro("status", "Status deve ser ENTREGUE ou PENDENTE")
    c.validar()
    alvo = one(
        """SELECT 1 FROM atividade at JOIN turma_disciplina td ON td.id_turma_disciplina = at.id_turma_disciplina
             JOIN aluno a ON a.id_turma = td.id_turma WHERE at.id_atividade = ? AND a.id_aluno = ?""",
        (id_, g.user["id"]),
    )
    if not alvo:
        raise ApiError(404, "Atividade não encontrada para a sua turma")
    atual = one("SELECT status FROM entrega_atividade WHERE id_atividade = ? AND id_aluno = ?", (id_, g.user["id"]))
    if atual and atual["status"] == "CORRIGIDA":
        raise ApiError(409, "Atividade já corrigida; não é possível alterar a entrega")
    execute(
        """INSERT INTO entrega_atividade (id_atividade, id_aluno, status, entregue_em)
           VALUES (?, ?, ?, CASE WHEN ? = 'ENTREGUE' THEN datetime('now','localtime') END)
           ON CONFLICT (id_atividade, id_aluno)
           DO UPDATE SET status = excluded.status, entregue_em = excluded.entregue_em""",
        (id_, g.user["id"], status, status),
    )
    return jsonify(id=id_, statusEntrega=status)
