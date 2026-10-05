"""Consultas de usuário (com dados específicos de cada perfil)."""
from ..db import one, rows

_SELECT = """
  SELECT u.id_usuario AS id, u.nome, u.email, u.perfil, u.ativo,
         a.matricula, a.serie, a.data_nascimento AS dataNascimento,
         a.id_turma AS idTurma, t.nome AS turma,
         r.telefone, p.especialidade, c.cargo
    FROM usuario u
    LEFT JOIN aluno a        ON a.id_aluno = u.id_usuario
    LEFT JOIN turma t        ON t.id_turma = a.id_turma
    LEFT JOIN responsavel r  ON r.id_responsavel = u.id_usuario
    LEFT JOIN professor p    ON p.id_professor = u.id_usuario
    LEFT JOIN coordenador c  ON c.id_coordenador = u.id_usuario"""


def usuario_por_id(id_: int) -> dict | None:
    u = one(f"{_SELECT} WHERE u.id_usuario = ?", (id_,))
    if not u:
        return None
    u["ativo"] = bool(u["ativo"])
    if u["perfil"] == "ALUNO":
        u["responsaveis"] = rows(
            """SELECT ar.id_responsavel AS idResponsavel, us.nome, ar.grau_parentesco AS grauParentesco
                 FROM aluno_responsavel ar JOIN usuario us ON us.id_usuario = ar.id_responsavel
                WHERE ar.id_aluno = ? ORDER BY us.nome""",
            (id_,),
        )
    if u["perfil"] == "RESPONSAVEL":
        u["alunos"] = rows(
            """SELECT ar.id_aluno AS idAluno, us.nome, ar.grau_parentesco AS grauParentesco
                 FROM aluno_responsavel ar JOIN usuario us ON us.id_usuario = ar.id_aluno
                WHERE ar.id_responsavel = ? ORDER BY us.nome""",
            (id_,),
        )
    return u


def listar_usuarios(perfis: list[str], q: str | None = None) -> list[dict]:
    where, params = [], []
    if perfis:
        where.append(f"u.perfil IN ({','.join('?' * len(perfis))})")
        params += perfis
    if q:
        like = f"%{q.lower()}%"
        where.append("(lower(u.nome) LIKE ? OR lower(u.email) LIKE ? OR lower(COALESCE(a.matricula,'')) LIKE ?)")
        params += [like, like, like]
    sql = f"{_SELECT} {'WHERE ' + ' AND '.join(where) if where else ''} ORDER BY u.nome LIMIT 500"
    out = rows(sql, params)
    for u in out:
        u["ativo"] = bool(u["ativo"])
    return out
