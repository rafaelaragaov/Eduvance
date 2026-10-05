"""Cadastro e gerenciamento de usuários (PB03-PB06).

 - ADMIN: gerencia qualquer perfil.
 - COORDENADOR: gerencia apenas PROFESSOR (requisito 6.6 da Sprint 01).
"""
from flask import Blueprint, g, jsonify, request

from ..db import execute, one, transacao
from ..errors import ApiError, Corpo, nao_encontrado, proibido
from ..security import PERFIS, auth_required, hash_senha
from ..services.usuarios import listar_usuarios, usuario_por_id

bp = Blueprint("usuarios", __name__, url_prefix="/api/usuarios")


def _perfis_permitidos(perfil: str) -> tuple[str, ...]:
    return PERFIS if perfil == "ADMIN" else ("PROFESSOR",)


def _validar_comum(c: Corpo, criando: bool) -> dict:
    d = {
        "nome": c.texto("nome", "Nome", minimo=3, maximo=120),
        "email": c.email(),
    }
    senha = c.texto("senha", "Senha", minimo=6, maximo=72, obrigatorio=criando)
    d["senha"] = senha
    d["ativo"] = c.d.get("ativo") if isinstance(c.d.get("ativo"), bool) else None
    d["matricula"] = c.texto("matricula", "Matrícula", minimo=3, maximo=20, obrigatorio=False)
    d["serie"] = c.texto("serie", "Série", maximo=40, obrigatorio=False)
    d["telefone"] = c.texto("telefone", "Telefone", maximo=30, obrigatorio=False)
    d["especialidade"] = c.texto("especialidade", "Especialidade", maximo=80, obrigatorio=False)
    d["cargo"] = c.texto("cargo", "Cargo", maximo=80, obrigatorio=False)
    d["dataNascimento"] = c.data("dataNascimento", "Data de nascimento", obrigatorio=False)
    d["idTurma"] = c.inteiro("idTurma", "Turma", obrigatorio=False)
    resp = c.d.get("responsaveis")
    d["responsaveis"] = None
    if resp is not None:
        if not isinstance(resp, list):
            c._erro("responsaveis", "Responsáveis deve ser uma lista")
        elif len(resp) > 2:
            c._erro("responsaveis", "Um aluno pode ter no máximo 2 responsáveis")
        else:
            lista = []
            for r in resp:
                try:
                    lista.append((int(r["idResponsavel"]), (r.get("grauParentesco") or None)))
                except (KeyError, TypeError, ValueError, AttributeError):
                    c._erro("responsaveis", "Responsável inválido")
            if len({i for i, _ in lista}) != len(lista):
                c._erro("responsaveis", "Responsável repetido")
            d["responsaveis"] = lista
    return d


def _gravar_perfil(con, id_: int, perfil: str, d: dict, c: Corpo, criando: bool):
    if perfil == "ALUNO":
        if criando:
            con.execute(
                "INSERT INTO aluno (id_aluno, matricula, data_nascimento, serie, id_turma) VALUES (?,?,?,?,?)",
                (id_, d["matricula"], d["dataNascimento"], d["serie"], d["idTurma"]),
            )
        else:
            sets, p = [], []
            for campo, col in (("matricula", "matricula"), ("dataNascimento", "data_nascimento"), ("serie", "serie"), ("idTurma", "id_turma")):
                if c.tem(campo) and (campo != "matricula" or d["matricula"]):
                    sets.append(f"{col} = ?")
                    p.append(d[campo])
            if sets:
                con.execute(f"UPDATE aluno SET {', '.join(sets)} WHERE id_aluno = ?", (*p, id_))
        if d["responsaveis"] is not None:
            con.execute("DELETE FROM aluno_responsavel WHERE id_aluno = ?", (id_,))
            for id_resp, grau in d["responsaveis"]:
                ok = con.execute("SELECT 1 FROM usuario WHERE id_usuario = ? AND perfil = 'RESPONSAVEL'", (id_resp,)).fetchone()
                if not ok:
                    raise ApiError(400, f"Responsável {id_resp} inválido")
                con.execute("INSERT INTO aluno_responsavel (id_aluno, id_responsavel, grau_parentesco) VALUES (?,?,?)", (id_, id_resp, grau))
        return
    tabela = {
        "RESPONSAVEL": ("responsavel", "id_responsavel", "telefone", "telefone"),
        "PROFESSOR": ("professor", "id_professor", "especialidade", "especialidade"),
        "COORDENADOR": ("coordenador", "id_coordenador", "cargo", "cargo"),
    }.get(perfil)
    if tabela:
        tab, pk, col, campo = tabela
        if criando:
            con.execute(f"INSERT INTO {tab} ({pk}, {col}) VALUES (?,?)", (id_, d[campo]))
        elif c.tem(campo):
            con.execute(f"UPDATE {tab} SET {col} = ? WHERE {pk} = ?", (d[campo], id_))


@bp.get("")
@auth_required("ADMIN", "COORDENADOR")
def listar():
    permitidos = _perfis_permitidos(g.user["perfil"])
    pedido = request.args.get("perfil", "")
    perfis = [p for p in (x.strip().upper() for x in pedido.split(",") if x.strip()) if p in permitidos] or list(permitidos)
    return jsonify(listar_usuarios(perfis, request.args.get("q", "").strip() or None))


@bp.get("/<int:id_>")
@auth_required("ADMIN", "COORDENADOR")
def obter(id_):
    u = usuario_por_id(id_)
    if not u:
        raise nao_encontrado("Usuário")
    if u["perfil"] not in _perfis_permitidos(g.user["perfil"]):
        raise proibido()
    return jsonify(u)


@bp.post("")
@auth_required("ADMIN", "COORDENADOR")
def criar():
    """Cadastro de usuário (persistido no banco)."""
    c = Corpo(request.get_json(silent=True))
    perfil = c.texto("perfil", "Perfil")
    if perfil and perfil not in PERFIS:
        c._erro("perfil", "Perfil inválido")
    d = _validar_comum(c, criando=True)
    if perfil == "ALUNO" and not d["matricula"]:
        c._erro("matricula", "Matrícula é obrigatória para alunos")
    c.validar()
    if perfil not in _perfis_permitidos(g.user["perfil"]):
        raise proibido(f"Seu perfil não pode cadastrar usuários do tipo {perfil}")

    with transacao() as con:
        cur = con.execute(
            "INSERT INTO usuario (nome, email, senha_hash, perfil, ativo) VALUES (?,?,?,?,?)",
            (d["nome"], d["email"], hash_senha(d["senha"]), perfil, 0 if d["ativo"] is False else 1),
        )
        _gravar_perfil(con, cur.lastrowid, perfil, d, c, criando=True)
        novo = cur.lastrowid
    return jsonify(usuario_por_id(novo)), 201


@bp.put("/<int:id_>")
@auth_required("ADMIN", "COORDENADOR")
def atualizar(id_):
    atual = usuario_por_id(id_)
    if not atual:
        raise nao_encontrado("Usuário")
    if atual["perfil"] not in _perfis_permitidos(g.user["perfil"]):
        raise proibido()
    c = Corpo(request.get_json(silent=True))
    d = _validar_comum(c, criando=False)
    c.validar()
    if id_ == g.user["id"] and d["ativo"] is False:
        raise ApiError(400, "Você não pode desativar a própria conta")

    with transacao() as con:
        con.execute(
            """UPDATE usuario SET nome = ?, email = ?, ativo = COALESCE(?, ativo), senha_hash = COALESCE(?, senha_hash)
                WHERE id_usuario = ?""",
            (d["nome"], d["email"], None if d["ativo"] is None else int(d["ativo"]), hash_senha(d["senha"]) if d["senha"] else None, id_),
        )
        _gravar_perfil(con, id_, atual["perfil"], d, c, criando=False)
    return jsonify(usuario_por_id(id_))


@bp.delete("/<int:id_>")
@auth_required("ADMIN", "COORDENADOR")
def excluir(id_):
    if id_ == g.user["id"]:
        raise ApiError(400, "Você não pode excluir a própria conta")
    atual = usuario_por_id(id_)
    if not atual:
        raise nao_encontrado("Usuário")
    if atual["perfil"] not in _perfis_permitidos(g.user["perfil"]):
        raise proibido()
    execute("DELETE FROM usuario WHERE id_usuario = ?", (id_,))
    return "", 204
