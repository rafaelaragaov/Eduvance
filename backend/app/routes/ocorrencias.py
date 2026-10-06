"""Ocorrências escolares (PB19) — módulo Comunicação Escolar (Sprint 05).

Fluxo: o professor registra → a coordenação é notificada, analisa e resolve (com parecer) → professor e
responsáveis são avisados. Cada mudança de situação fica no histórico.

 - PROFESSOR: registra para alunos de suas turmas; vê, edita (enquanto ABERTA) e exclui as que registrou.
 - COORDENADOR e ADMIN: veem todas, registram, alteram a situação (só para frente) e resolvem com parecer.
 - ALUNO: vê as próprias. RESPONSAVEL: vê as dos alunos vinculados.
"""
from datetime import date, datetime

from flask import Blueprint, g, jsonify, request

from ..db import execute, one, rows, transacao
from ..errors import ApiError, Corpo, nao_encontrado, proibido
from ..security import auth_required
from ..services import comunicacao as cm
from ..services.acesso import pode_ver_aluno

bp = Blueprint("ocorrencias", __name__, url_prefix="/api/ocorrencias")

TIPOS = ["DISCIPLINAR", "PEDAGOGICA", "SAUDE", "ELOGIO"]
GRAVIDADES = ["LEVE", "MEDIA", "GRAVE"]
STATUS = ["ABERTA", "EM_ANALISE", "RESOLVIDA"]
ROTULO_STATUS = {"ABERTA": "Aberta", "EM_ANALISE": "Em análise", "RESOLVIDA": "Resolvida"}

_BASE = """
  SELECT o.id_ocorrencia AS id, o.id_aluno AS idAluno, ua.nome AS aluno, t.nome AS turma, a.matricula,
         o.id_professor AS idProfessor, up.nome AS professor, o.titulo, o.descricao, o.tipo, o.gravidade,
         o.status, o.data_ocorrencia AS data, o.parecer, o.resolvida_em AS resolvidaEm
    FROM ocorrencia o
    JOIN aluno a ON a.id_aluno = o.id_aluno
    JOIN usuario ua ON ua.id_usuario = a.id_aluno
    LEFT JOIN turma t ON t.id_turma = a.id_turma
    LEFT JOIN usuario up ON up.id_usuario = o.id_professor"""


def _escopo(user: dict) -> tuple[str, list]:
    p, uid = user["perfil"], user["id"]
    if p in ("ADMIN", "COORDENADOR"):
        return "1 = 1", []
    if p == "ALUNO":
        return "o.id_aluno = ?", [uid]
    if p == "RESPONSAVEL":
        return "o.id_aluno IN (SELECT id_aluno FROM aluno_responsavel WHERE id_responsavel = ?)", [uid]
    return "o.id_professor = ?", [uid]


def _pode_editar(user: dict, o: dict) -> bool:
    if o["status"] == "RESOLVIDA":
        return False
    if user["perfil"] in ("ADMIN", "COORDENADOR"):
        return True
    return user["perfil"] == "PROFESSOR" and o["idProfessor"] == user["id"] and o["status"] == "ABERTA"


def _formatar(o: dict, user: dict) -> dict:
    o["podeEditar"] = _pode_editar(user, o)
    o["podeAlterarStatus"] = user["perfil"] in ("ADMIN", "COORDENADOR") and o["status"] != "RESOLVIDA"
    return o


def _visivel(id_: int) -> dict:
    esc, p = _escopo(g.user)
    o = one(_BASE + f" WHERE o.id_ocorrencia = ? AND {esc}", (id_, *p))
    if not o:
        raise nao_encontrado("Ocorrência", feminino=True)
    return _formatar(o, g.user)


def _historico(id_: int) -> list[dict]:
    return rows(
        """SELECT h.id_historico AS id, h.status_anterior AS statusAnterior, h.status_novo AS statusNovo,
                  h.comentario, h.criado_em AS data, COALESCE(u.nome, 'Usuário removido') AS usuario
             FROM ocorrencia_historico h LEFT JOIN usuario u ON u.id_usuario = h.id_usuario
            WHERE h.id_ocorrencia = ? ORDER BY h.id_historico""",
        (id_,),
    )


@bp.get("")
@auth_required()
def listar():
    esc, params = _escopo(g.user)
    where = [esc]
    for arg, col, opcoes in (("status", "o.status", STATUS), ("gravidade", "o.gravidade", GRAVIDADES), ("tipo", "o.tipo", TIPOS)):
        v = request.args.get(arg)
        if v:
            if v not in opcoes:
                raise ApiError(400, f"Filtro inválido: {arg}", [{"campo": arg, "mensagem": f"Use um de: {', '.join(opcoes)}"}])
            where.append(f"{col} = ?")
            params.append(v)
    ida = request.args.get("idAluno", type=int)
    if ida:
        where.append("o.id_aluno = ?")
        params.append(ida)
    busca = (request.args.get("busca") or "").strip().lower()
    if busca:
        where.append("(lower(ua.nome) LIKE ? OR lower(o.titulo) LIKE ?)")
        params += [f"%{busca}%"] * 2
    sql = _BASE + " WHERE " + " AND ".join(where) + " ORDER BY CASE o.status WHEN 'ABERTA' THEN 0 WHEN 'EM_ANALISE' THEN 1 ELSE 2 END, o.data_ocorrencia DESC, o.id_ocorrencia DESC"
    return jsonify([_formatar(o, g.user) for o in rows(sql, params)])


@bp.get("/resumo")
@auth_required()
def resumo():
    esc, params = _escopo(g.user)
    r = rows(f"SELECT o.status, COUNT(*) AS n FROM ocorrencia o WHERE {esc} GROUP BY o.status", params)
    out = {s: 0 for s in STATUS}
    out.update({x["status"]: x["n"] for x in r})
    return jsonify(out)


@bp.get("/<int:id_>")
@auth_required()
def obter(id_):
    o = _visivel(id_)
    o["historico"] = _historico(id_)
    return jsonify(o)


def _corpo(parcial=False) -> dict:
    c = Corpo(request.get_json(silent=True))
    d = {
        "titulo": c.texto("titulo", "Título", minimo=3, maximo=120),
        "descricao": c.texto("descricao", "Descrição", minimo=10, maximo=2000),
        "tipo": c.opcao("tipo", "Tipo", TIPOS),
        "gravidade": c.opcao("gravidade", "Gravidade", GRAVIDADES, obrigatorio=False, padrao="LEVE"),
    }
    if not parcial:
        d["idAluno"] = c.inteiro("idAluno", "Aluno")
        d["dataOcorrencia"] = c.data("dataOcorrencia", "Data da ocorrência", obrigatorio=False)
    if d["tipo"] == "ELOGIO" and d["gravidade"] != "LEVE":
        c._erro("gravidade", "Elogios não possuem gravidade (use \"Leve\")")
    if not parcial and d.get("dataOcorrencia") and datetime.strptime(d["dataOcorrencia"], "%Y-%m-%d").date() > date.today():
        c._erro("dataOcorrencia", "A data da ocorrência não pode ser futura")
    c.validar()
    return d


@bp.post("")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def registrar():
    d = _corpo()
    u = g.user
    aluno = one("SELECT u.nome FROM aluno a JOIN usuario u ON u.id_usuario = a.id_aluno WHERE a.id_aluno = ?", (d["idAluno"],))
    if not aluno:
        raise ApiError(400, "Dados inválidos", [{"campo": "idAluno", "mensagem": "Aluno inexistente"}])
    if not pode_ver_aluno(u, d["idAluno"]):
        raise proibido("Você só pode registrar ocorrências de alunos das turmas em que leciona")

    quando = f"{d['dataOcorrencia']}T{datetime.now():%H:%M:%S}" if d.get("dataOcorrencia") else datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    dia = quando[:10]
    if one("SELECT 1 FROM ocorrencia WHERE id_aluno = ? AND lower(titulo) = lower(?) AND substr(data_ocorrencia,1,10) = ? AND id_professor IS ?",
           (d["idAluno"], d["titulo"], dia, u["id"] if u["perfil"] == "PROFESSOR" else None)):
        raise ApiError(409, "Esta ocorrência já foi registrada para o aluno nesta data",
                       [{"campo": "titulo", "mensagem": "Já existe uma ocorrência com este título para o aluno no mesmo dia"}])

    with transacao() as con:
        novo = con.execute(
            "INSERT INTO ocorrencia (id_aluno, id_professor, titulo, descricao, data_ocorrencia, tipo, gravidade) VALUES (?,?,?,?,?,?,?)",
            (d["idAluno"], u["id"] if u["perfil"] == "PROFESSOR" else None, d["titulo"], d["descricao"], quando, d["tipo"], d["gravidade"]),
        ).lastrowid
        con.execute("INSERT INTO ocorrencia_historico (id_ocorrencia, id_usuario, status_anterior, status_novo, comentario) VALUES (?,?,NULL,'ABERTA','Ocorrência registrada')",
                    (novo, u["id"]))
        link = f"/ocorrencias/{novo}"
        cm.notificar(cm.coordenadores(), "OCORRENCIA", f"Nova ocorrência: {aluno['nome']}", f"{d['titulo']} ({d['gravidade'].lower()}).", link, ignorar=u["id"], con=con)
        if d["gravidade"] in ("MEDIA", "GRAVE") or d["tipo"] == "ELOGIO":
            cm.notificar(cm.responsaveis_do_aluno(d["idAluno"]), "OCORRENCIA",
                         f"{'Elogio' if d['tipo'] == 'ELOGIO' else 'Ocorrência'} sobre {aluno['nome']}", d["titulo"], link, con=con)
    return jsonify(_visivel(novo)), 201


@bp.put("/<int:id_>")
@auth_required("PROFESSOR", "COORDENADOR", "ADMIN")
def atualizar(id_):
    atual = _visivel(id_)
    if atual["status"] == "RESOLVIDA":
        raise ApiError(409, "Ocorrência resolvida não pode ser editada")
    if not atual["podeEditar"]:
        raise proibido("Você só pode editar suas próprias ocorrências enquanto estiverem abertas")
    d = _corpo(parcial=True)
    execute("UPDATE ocorrencia SET titulo = ?, descricao = ?, tipo = ?, gravidade = ? WHERE id_ocorrencia = ?",
            (d["titulo"], d["descricao"], d["tipo"], d["gravidade"], id_))
    return jsonify(_visivel(id_))


@bp.put("/<int:id_>/status")
@auth_required("COORDENADOR", "ADMIN")
def alterar_status(id_):
    """Coloca a ocorrência em análise ou a resolve (parecer obrigatório). Só avança: ABERTA → EM_ANALISE → RESOLVIDA."""
    atual = _visivel(id_)
    c = Corpo(request.get_json(silent=True))
    novo = c.opcao("status", "Situação", STATUS)
    parecer = c.texto("parecer", "Parecer", minimo=10, maximo=1000, obrigatorio=(novo == "RESOLVIDA"))
    c.validar()
    if STATUS.index(novo) <= STATUS.index(atual["status"]):
        raise ApiError(409, f"A ocorrência já está \"{ROTULO_STATUS[atual['status']]}\"; a situação só pode avançar",
                       [{"campo": "status", "mensagem": "Situação inválida para o estado atual"}])
    with transacao() as con:
        con.execute(
            "UPDATE ocorrencia SET status = ?, parecer = COALESCE(?, parecer), resolvida_em = CASE WHEN ? = 'RESOLVIDA' THEN datetime('now','localtime') ELSE resolvida_em END WHERE id_ocorrencia = ?",
            (novo, parecer, novo, id_),
        )
        con.execute("INSERT INTO ocorrencia_historico (id_ocorrencia, id_usuario, status_anterior, status_novo, comentario) VALUES (?,?,?,?,?)",
                    (id_, g.user["id"], atual["status"], novo, parecer))
        avisar = [atual["idProfessor"]] if atual["idProfessor"] else []
        if novo == "RESOLVIDA":
            avisar += cm.responsaveis_do_aluno(atual["idAluno"])
        cm.notificar(avisar, "OCORRENCIA", f"Ocorrência {ROTULO_STATUS[novo].lower()}: {atual['aluno']}", atual["titulo"],
                     f"/ocorrencias/{id_}", ignorar=g.user["id"], con=con)
    o = _visivel(id_)
    o["historico"] = _historico(id_)
    return jsonify(o)


@bp.delete("/<int:id_>")
@auth_required("PROFESSOR", "ADMIN")
def excluir(id_):
    atual = _visivel(id_)
    if g.user["perfil"] == "PROFESSOR" and (atual["idProfessor"] != g.user["id"] or atual["status"] != "ABERTA"):
        raise proibido("Você só pode excluir suas próprias ocorrências enquanto estiverem abertas")
    execute("DELETE FROM ocorrencia WHERE id_ocorrencia = ?", (id_,))
    return "", 204
