"""Regras de quem pode ver/alterar o quê (escopo por perfil)."""
from ..db import one, rows


def pode_ver_aluno(user: dict, id_aluno: int) -> bool:
    p = user["perfil"]
    if p in ("ADMIN", "COORDENADOR"):
        return True
    if p == "ALUNO":
        return user["id"] == id_aluno
    if p == "RESPONSAVEL":
        return bool(one("SELECT 1 FROM aluno_responsavel WHERE id_aluno=? AND id_responsavel=?", (id_aluno, user["id"])))
    if p == "PROFESSOR":
        return bool(one(
            """SELECT 1 FROM aluno a JOIN turma_disciplina td ON td.id_turma = a.id_turma
                WHERE a.id_aluno = ? AND td.id_professor = ? LIMIT 1""",
            (id_aluno, user["id"]),
        ))
    return False


def pode_gerir_turma_disciplina(user: dict, id_td: int) -> bool:
    if user["perfil"] in ("ADMIN", "COORDENADOR"):
        return True
    if user["perfil"] != "PROFESSOR":
        return False
    return bool(one("SELECT 1 FROM turma_disciplina WHERE id_turma_disciplina=? AND id_professor=?", (id_td, user["id"])))


def alunos_vinculados(id_responsavel: int) -> list[dict]:
    return rows(
        """SELECT u.id_usuario AS id, u.nome FROM aluno_responsavel ar
             JOIN usuario u ON u.id_usuario = ar.id_aluno
            WHERE ar.id_responsavel = ? ORDER BY ar.id_aluno""",
        (id_responsavel,),
    )
