"""Comunicados (PB18) — módulo Comunicação Escolar (Sprint 05).

 - ADMIN e COORDENADOR: publicam para qualquer público (todos, alunos, responsáveis, professores ou uma turma).
 - PROFESSOR: publica apenas para uma turma em que leciona.
 - Todos os perfis leem os comunicados dirigidos a eles e marcam como lido.
 - Editar/excluir: o autor, a coordenação ou o administrador. O público não muda depois de publicado.
"""
from flask import Blueprint, g, jsonify, request

from ..db import execute, one, rows, scalar, transacao
from ..errors import ApiError, Corpo, nao_encontrado, proibido
from ..security import auth_required
from ..services import comunicacao as cm

bp = Blueprint("comunicados", __name__, url_prefix="/api/comunicados")

JANELA_DUPLICIDADE_MIN = 5


def _consulta(user: dict, extra: str = "", params=()) -> tuple[str, list]:
    filtro, p = cm.filtro_comunicados(user)
    sql = f"""
      SELECT c.id_comunicado AS id, c.titulo, c.mensagem, c.data_publicacao AS dataPublicacao,
             c.publico, c.id_turma AS idTurma, t.nome AS turma,
             c.id_usuario_autor AS idAutor, COALESCE(u.nome, 'Usuário removido') AS autor, u.perfil AS perfilAutor,
             CASE WHEN c.id_usuario_autor = ? OR EXISTS (SELECT 1 FROM comunicado_leitura l WHERE l.id_comunicado = c.id_comunicado AND l.id_usuario = ?)
                  THEN 1 ELSE 0 END AS lido
        FROM comunicado c
        LEFT JOIN usuario u ON u.id_usuario = c.id_usuario_autor
        LEFT JOIN turma t ON t.id_turma = c.id_turma
       WHERE {filtro} {extra}"""
    return sql, [user["id"], user["id"], *p, *params]


def _pode_alterar(user: dict, c: dict) -> bool:
    return user["perfil"] in ("ADMIN", "COORDENADOR") or c["idAutor"] == user["id"]


def _formatar(c: dict, user: dict) -> dict:
    c["lido"] = bool(c["lido"])
    c["podeAlterar"] = _pode_alterar(user, c)
    return c


@bp.get("")
@auth_required()
def listar():
    extra, params = "", []
    if request.args.get("lido") == "nao":
        extra += " AND c.id_usuario_autor IS NOT ? AND NOT EXISTS (SELECT 1 FROM comunicado_leitura l WHERE l.id_comunicado = c.id_comunicado AND l.id_usuario = ?)"
        params += [g.user["id"], g.user["id"]]
    busca = (request.args.get("busca") or "").strip()
    if busca:
        extra += " AND (lower(c.titulo) LIKE ? OR lower(c.mensagem) LIKE ?)"
        params += [f"%{busca.lower()}%"] * 2
    sql, p = _consulta(g.user, extra, params)
    return jsonify([_formatar(c, g.user) for c in rows(sql + " ORDER BY c.data_publicacao DESC, c.id_comunicado DESC", p)])


@bp.get("/nao-lidos")
@auth_required()
def nao_lidos():
    sql, p = _consulta(g.user, " AND c.id_usuario_autor IS NOT ? AND NOT EXISTS (SELECT 1 FROM comunicado_leitura l WHERE l.id_comunicado = c.id_comunicado AND l.id_usuario = ?)",
                       [g.user["id"], g.user["id"]])
    return jsonify(total=len(rows(sql, p)))


def _visivel(id_: int) -> dict:
    sql, p = _consulta(g.user, " AND c.id_comunicado = ?", [id_])
    c = one(sql, p)
    if not c:
        raise nao_encontrado("Comunicado")
    return _formatar(c, g.user)


@bp.get("/<int:id_>")
@auth_required()
def obter(id_):
    c = _visivel(id_)
    if c["podeAlterar"]:  # quem publicou acompanha a leitura
        destinatarios = [u for u in cm.destinatarios_comunicado(c["publico"], c["idTurma"]) if u != c["idAutor"]]
        lidos = scalar("SELECT COUNT(*) FROM comunicado_leitura WHERE id_comunicado = ?", (id_,))
        c["leitura"] = {"lidos": lidos, "destinatarios": len(destinatarios)}
    return jsonify(c)


@bp.put("/<int:id_>/lido")
@auth_required()
def marcar_lido(id_):
    _visivel(id_)
    execute("INSERT OR IGNORE INTO comunicado_leitura (id_comunicado, id_usuario) VALUES (?,?)", (id_, g.user["id"]))
    return jsonify(_visivel(id_))


def _corpo_novo() -> dict:
    c = Corpo(request.get_json(silent=True))
    d = {
        "titulo": c.texto("titulo", "Título", minimo=3, maximo=120),
        "mensagem": c.texto("mensagem", "Mensagem", minimo=10, maximo=2000),
        "publico": c.opcao("publico", "Público", cm.PUBLICOS),
        "idTurma": c.inteiro("idTurma", "Turma", obrigatorio=False),
    }
    if d["publico"] == "TURMA" and d["idTurma"] is None:
        c._erro("idTurma", "Escolha a turma que receberá o comunicado")
    if d["publico"] and d["publico"] != "TURMA" and d["idTurma"] is not None:
        c._erro("idTurma", "A turma só deve ser informada quando o público for \"Turma\"")
    c.validar()
    return d


@bp.post("")
@auth_required("ADMIN", "COORDENADOR", "PROFESSOR")
def publicar():
    d = _corpo_novo()
    u = g.user
    if d["publico"] == "TURMA":
        if not one("SELECT 1 FROM turma WHERE id_turma = ?", (d["idTurma"],)):
            raise ApiError(400, "Dados inválidos", [{"campo": "idTurma", "mensagem": "Turma inexistente"}])
        if u["perfil"] == "PROFESSOR" and not one("SELECT 1 FROM turma_disciplina WHERE id_turma = ? AND id_professor = ?", (d["idTurma"], u["id"])):
            raise proibido("Você só pode publicar comunicados para turmas em que leciona")
    elif u["perfil"] == "PROFESSOR":
        raise proibido("Professores publicam comunicados apenas para uma de suas turmas")

    repetido = one(
        """SELECT id_comunicado FROM comunicado
            WHERE id_usuario_autor = ? AND lower(titulo) = lower(?) AND publico = ? AND id_turma IS ?
              AND data_publicacao >= datetime('now', 'localtime', ?)""",
        (u["id"], d["titulo"], d["publico"], d["idTurma"], f"-{JANELA_DUPLICIDADE_MIN} minutes"),
    )
    if repetido:
        raise ApiError(409, "Este comunicado já foi publicado há instantes. Evite publicar o mesmo aviso duas vezes",
                       [{"campo": "titulo", "mensagem": "Comunicado repetido nos últimos minutos"}])

    with transacao() as con:
        novo = con.execute(
            "INSERT INTO comunicado (titulo, mensagem, id_usuario_autor, publico, id_turma, data_publicacao) VALUES (?,?,?,?,?, datetime('now','localtime'))",
            (d["titulo"], d["mensagem"], u["id"], d["publico"], d["idTurma"]),
        ).lastrowid
        n = cm.notificar(cm.destinatarios_comunicado(d["publico"], d["idTurma"]), "COMUNICADO",
                         f"Novo comunicado: {d['titulo']}", f"Publicado por {u['nome']}.", "/comunicados", ignorar=u["id"], con=con)
    resp = _visivel(novo)
    resp["notificados"] = n
    return jsonify(resp), 201


@bp.put("/<int:id_>")
@auth_required("ADMIN", "COORDENADOR", "PROFESSOR")
def atualizar(id_):
    atual = _visivel(id_)
    if not atual["podeAlterar"]:
        raise proibido("Somente o autor, a coordenação ou o administrador podem editar este comunicado")
    c = Corpo(request.get_json(silent=True))
    titulo = c.texto("titulo", "Título", minimo=3, maximo=120)
    mensagem = c.texto("mensagem", "Mensagem", minimo=10, maximo=2000)
    if c.tem("publico") and c.d["publico"] != atual["publico"]:
        c._erro("publico", "O público não pode ser alterado depois da publicação; publique um novo comunicado")
    c.validar()
    execute("UPDATE comunicado SET titulo = ?, mensagem = ? WHERE id_comunicado = ?", (titulo, mensagem, id_))
    return jsonify(_visivel(id_))


@bp.delete("/<int:id_>")
@auth_required("ADMIN", "COORDENADOR", "PROFESSOR")
def excluir(id_):
    atual = _visivel(id_)
    if not atual["podeAlterar"]:
        raise proibido("Somente o autor, a coordenação ou o administrador podem excluir este comunicado")
    execute("DELETE FROM comunicado WHERE id_comunicado = ?", (id_,))
    return "", 204
