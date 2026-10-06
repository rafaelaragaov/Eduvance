"""Lançamento de notas (PB11): professor da turma, coordenador e administrador."""
from flask import Blueprint, current_app, g, jsonify, request

from ..db import execute, one, rows, transacao
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
        raise nao_encontrado("Avaliação", feminino=True)
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


# ---------------------------------------------------------------------------
# Lançamento em lote por avaliação (Sprint 04)
# ---------------------------------------------------------------------------
def _avaliacao_com_alunos(id_av: int) -> dict:
    av = one(
        """SELECT av.id_avaliacao AS id, av.titulo, av.tipo, av.bimestre, av.data_avaliacao AS data, av.peso,
                  av.id_turma_disciplina AS idTurmaDisciplina, t.nome AS turma, d.nome AS disciplina
             FROM avaliacao av
             JOIN turma_disciplina td ON td.id_turma_disciplina = av.id_turma_disciplina
             JOIN turma t ON t.id_turma = td.id_turma
             JOIN disciplina d ON d.id_disciplina = td.id_disciplina
            WHERE av.id_avaliacao = ?""",
        (id_av,),
    )
    if not av:
        raise nao_encontrado("Avaliação", feminino=True)
    if not pode_gerir_turma_disciplina(g.user, av["idTurmaDisciplina"]):
        raise proibido()
    alunos = rows(
        """SELECT a.id_aluno AS idAluno, u.nome, a.matricula, n.valor AS valor
             FROM turma_disciplina td
             JOIN aluno a ON a.id_turma = td.id_turma
             JOIN usuario u ON u.id_usuario = a.id_aluno
             LEFT JOIN nota n ON n.id_aluno = a.id_aluno AND n.id_avaliacao = ?
            WHERE td.id_turma_disciplina = ?
            ORDER BY u.nome""",
        (id_av, av["idTurmaDisciplina"]),
    )
    valores = [a["valor"] for a in alunos if a["valor"] is not None]
    return {"avaliacao": av, "alunos": alunos, "media": round(sum(valores) / len(valores), 1) if valores else None}


@bp.get("/avaliacao/<int:id_av>")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def da_avaliacao(id_av):
    """Avaliação e a lista de alunos da turma com a nota atual de cada um."""
    return jsonify(_avaliacao_com_alunos(id_av))


@bp.put("/avaliacao/<int:id_av>")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def lancar_lote(id_av):
    """Grava, de uma vez e de forma atômica, as notas de uma avaliação.

    Corpo: {"notas": [{"idAluno": 1, "valor": 8.5}, {"idAluno": 2, "valor": null}]}
    Se qualquer linha for inválida, nada é gravado e o erro aponta o aluno (campo "nota-<idAluno>").
    """
    atual = _avaliacao_com_alunos(id_av)  # valida existência e permissão
    c = Corpo(request.get_json(silent=True))
    itens = c.d.get("notas")
    if not isinstance(itens, list) or not itens:
        raise ApiError(400, "Informe ao menos uma nota para salvar")
    turma_ids = {a["idAluno"] for a in atual["alunos"]}
    nomes = {a["idAluno"]: a["nome"] for a in atual["alunos"]}
    erros, validos, vistos = [], [], set()
    for i, it in enumerate(itens):
        if not isinstance(it, dict):
            erros.append({"campo": f"notas[{i}]", "mensagem": "Item inválido"})
            continue
        ida = it.get("idAluno")
        if not isinstance(ida, int) or isinstance(ida, bool) or ida not in turma_ids:
            erros.append({"campo": f"notas[{i}]", "mensagem": "Aluno não pertence a esta turma"})
            continue
        campo = f"nota-{ida}"
        if ida in vistos:
            erros.append({"campo": campo, "mensagem": f"{nomes[ida]}: aluno informado mais de uma vez"})
            continue
        vistos.add(ida)
        bruto = it.get("valor")
        if bruto is None or bruto == "":
            validos.append((ida, None))
            continue
        try:
            if isinstance(bruto, bool):
                raise ValueError
            v = float(str(bruto).replace(",", "."))
        except (TypeError, ValueError):
            erros.append({"campo": campo, "mensagem": f"{nomes[ida]}: a nota deve ser um número"})
            continue
        if not 0 <= v <= 10:
            erros.append({"campo": campo, "mensagem": f"{nomes[ida]}: a nota deve estar entre 0 e 10"})
            continue
        validos.append((ida, round(v, 1)))
    if erros:
        raise ApiError(400, "Corrija as notas inválidas antes de salvar", erros)

    with transacao() as con:
        for ida, v in validos:
            if v is None:
                con.execute("DELETE FROM nota WHERE id_avaliacao = ? AND id_aluno = ?", (id_av, ida))
            else:
                con.execute(
                    """INSERT INTO nota (id_avaliacao, id_aluno, valor) VALUES (?,?,?)
                       ON CONFLICT (id_avaliacao, id_aluno) DO UPDATE SET valor = excluded.valor""",
                    (id_av, ida, v),
                )
    novo = _avaliacao_com_alunos(id_av)
    return jsonify(salvas=sum(1 for _, v in validos if v is not None), removidas=sum(1 for _, v in validos if v is None), **novo)
