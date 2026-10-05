"""Dashboards por perfil (PB09) e resumo do aluno para o responsável."""
from flask import Blueprint, current_app, g, jsonify

from ..db import one, rows
from ..errors import nao_encontrado, proibido
from ..security import auth_required
from ..services import academico as ac
from ..services.acesso import alunos_vinculados, pode_ver_aluno

bp = Blueprint("dashboard", __name__, url_prefix="/api")


@bp.get("/dashboard")
@auth_required()
def dashboard():
    u = g.user
    fn = {
        "ALUNO": _aluno,
        "PROFESSOR": _professor,
        "COORDENADOR": lambda _id: _coordenador(),
        "RESPONSAVEL": _responsavel,
    }.get(u["perfil"], lambda _id: _admin())
    return jsonify(fn(u["id"]))


@bp.get("/alunos/<int:id_>/resumo")
@auth_required()
def resumo_aluno(id_):
    """Boletim rápido, mensalidades e ocorrências recentes de um aluno."""
    if not pode_ver_aluno(g.user, id_):
        raise proibido()
    a = one("SELECT nome FROM usuario WHERE id_usuario = ? AND perfil = 'ALUNO'", (id_,))
    if not a:
        raise nao_encontrado("Aluno")
    linhas = ac.boletim(id_)
    return jsonify(
        aluno={"id": id_, "nome": a["nome"]},
        boletim=linhas,
        mediaGeral=ac.media_geral(linhas),
        faltas=ac.faltas(id_),
        mensalidades=rows(
            """SELECT id_mensalidade AS id, valor, vencimento, status, forma_pagamento AS formaPagamento
                 FROM mensalidade WHERE id_aluno = ? ORDER BY vencimento DESC LIMIT 4""",
            (id_,),
        ),
        ocorrencias=rows(
            """SELECT id_ocorrencia AS id, titulo, descricao, data_ocorrencia AS data, status
                 FROM ocorrencia WHERE id_aluno = ? ORDER BY data_ocorrencia DESC LIMIT 3""",
            (id_,),
        ),
    )


# ---------------------------------------------------------------------------
def _aluno(id_: int) -> dict:
    cfg = current_app.config
    turma = (one("SELECT id_turma AS id FROM aluno WHERE id_aluno = ?", (id_,)) or {}).get("id")
    linhas = ac.boletim(id_)
    media = ac.media_geral(linhas)
    n_faltas = ac.faltas(id_)

    ativ = rows(
        """SELECT at.id_atividade AS id, at.titulo, at.data_entrega AS dataEntrega, d.nome AS disciplina,
                  COALESCE(ea.status,'PENDENTE') AS statusEntrega
             FROM aluno a
             JOIN turma_disciplina td ON td.id_turma = a.id_turma
             JOIN disciplina d ON d.id_disciplina = td.id_disciplina
             JOIN atividade at ON at.id_turma_disciplina = td.id_turma_disciplina
             LEFT JOIN entrega_atividade ea ON ea.id_atividade = at.id_atividade AND ea.id_aluno = a.id_aluno
            WHERE a.id_aluno = ? AND COALESCE(ea.status,'PENDENTE') = 'PENDENTE'
            ORDER BY at.data_entrega""",
        (id_,),
    )
    for a in ativ:
        a["urgencia"] = ac.urgencia(a["dataEntrega"], a["statusEntrega"])
    critico = any(a["urgencia"] in ("URGENTE", "ATRASADA") for a in ativ)

    return {
        "perfil": "ALUNO",
        "mediaGeral": media,
        "classificacaoMedia": ac.classifica_media(media),
        "faltas": n_faltas,
        "faltasStatus": "Dentro do limite" if n_faltas <= cfg["LIMITE_FALTAS"] else "Acima do limite",
        "faltasLimite": cfg["LIMITE_FALTAS"],
        "atividadesPendentes": len(ativ),
        "atividadesStatus": "Em dia" if not ativ else ("Atenção aos prazos" if critico else "Acompanhe"),
        "bimestre": cfg["BIMESTRE_ATUAL"],
        "boletim": linhas,
        "agendaHoje": ac.aulas_do_dia(turma_id=turma) if turma else [],
        "atividades": ativ[:3],
        "comunicados": rows(
            "SELECT id_comunicado AS id, titulo, mensagem, data_publicacao AS data FROM comunicado ORDER BY data_publicacao DESC LIMIT 3"
        ),
    }


def _professor(id_: int) -> dict:
    tds = rows(
        """SELECT td.id_turma_disciplina AS id, t.nome AS turma, d.nome AS disciplina,
                  (SELECT COUNT(*) FROM aluno a WHERE a.id_turma = t.id_turma) AS alunos
             FROM turma_disciplina td
             JOIN turma t ON t.id_turma = td.id_turma
             JOIN disciplina d ON d.id_disciplina = td.id_disciplina
            WHERE td.id_professor = ? ORDER BY td.id_turma_disciplina""",
        (id_,),
    )
    for td in tds:
        td["proximaAula"] = ac.proxima_aula(td["id"])
    return {"perfil": "PROFESSOR", "turmas": tds, "aulasHoje": ac.aulas_do_dia(professor_id=id_)}


def _coordenador() -> dict:
    cfg = current_app.config
    k = one(
        """SELECT (SELECT COUNT(*) FROM usuario WHERE perfil = 'PROFESSOR' AND ativo = 1) AS professores,
                  (SELECT COUNT(*) FROM ocorrencia WHERE status = 'ABERTA') AS ocorrencias,
                  (SELECT ROUND(100.0 * SUM(presente) / COUNT(*), 1) FROM frequencia) AS frequencia"""
    )
    return {
        "perfil": "COORDENADOR",
        "kpis": {
            "professoresAtivos": k["professores"],
            "ocorrenciasAbertas": k["ocorrencias"],
            "taxaFrequencia": k["frequencia"],
            "metaFrequencia": cfg["META_FREQUENCIA"],
        },
        "professores": rows(
            """SELECT u.id_usuario AS id, u.nome,
                      COALESCE((SELECT group_concat(nome, ', ') FROM (
                                  SELECT DISTINCT d.nome FROM turma_disciplina td
                                    JOIN disciplina d ON d.id_disciplina = td.id_disciplina
                                   WHERE td.id_professor = p.id_professor ORDER BY d.nome)),
                               p.especialidade, '—') AS disciplina
                 FROM professor p JOIN usuario u ON u.id_usuario = p.id_professor AND u.ativo = 1
                ORDER BY u.nome LIMIT 5"""
        ),
        "eventos": rows(
            "SELECT id_evento AS id, titulo, descricao, inicio FROM evento WHERE date(inicio) >= date('now','localtime') ORDER BY inicio LIMIT 4"
        ),
        "horariosHoje": ac.aulas_do_dia(),
        "ocorrencias": rows(
            """SELECT o.id_ocorrencia AS id, u.nome AS aluno, t.nome AS turma, o.titulo, o.descricao, o.data_ocorrencia AS data
                 FROM ocorrencia o
                 JOIN aluno a ON a.id_aluno = o.id_aluno
                 JOIN usuario u ON u.id_usuario = a.id_aluno
                 LEFT JOIN turma t ON t.id_turma = a.id_turma
                WHERE o.status = 'ABERTA' ORDER BY o.data_ocorrencia DESC LIMIT 4"""
        ),
    }


def _responsavel(id_: int) -> dict:
    alunos = []
    for v in alunos_vinculados(id_):
        info = one("SELECT t.nome AS turma, a.serie FROM aluno a LEFT JOIN turma t ON t.id_turma = a.id_turma WHERE a.id_aluno = ?", (v["id"],)) or {}
        alunos.append({
            "id": v["id"], "nome": v["nome"], "turma": info.get("turma"), "serie": info.get("serie"),
            "mediaGeral": ac.media_geral(ac.boletim(v["id"])), "faltas": ac.faltas(v["id"]),
        })
    return {"perfil": "RESPONSAVEL", "alunos": alunos}


def _admin() -> dict:
    por_perfil = {r["perfil"]: r["n"] for r in rows("SELECT perfil, COUNT(*) AS n FROM usuario GROUP BY perfil")}
    c = one("SELECT (SELECT COUNT(*) FROM turma) AS turmas, (SELECT COUNT(*) FROM disciplina) AS disciplinas, (SELECT COUNT(*) FROM atividade) AS atividades")
    return {"perfil": "ADMIN", "usuariosPorPerfil": por_perfil, **c}
