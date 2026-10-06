"""Regras do módulo Comunicação Escolar (Sprint 05): quem enxerga cada comunicado e quem recebe cada notificação."""
from ..db import get_db, rows

PUBLICOS = ["TODOS", "ALUNOS", "RESPONSAVEIS", "PROFESSORES", "TURMA"]


def filtro_comunicados(user: dict) -> tuple[str, list]:
    """Cláusula WHERE (sobre a tabela `c` = comunicado) com os comunicados que o usuário pode ver."""
    p, uid = user["perfil"], user["id"]
    if p in ("ADMIN", "COORDENADOR"):
        return "1 = 1", []
    if p == "ALUNO":
        return ("(c.publico IN ('TODOS','ALUNOS') OR (c.publico = 'TURMA' AND c.id_turma = "
                "(SELECT id_turma FROM aluno WHERE id_aluno = ?)))"), [uid]
    if p == "RESPONSAVEL":
        return ("(c.publico IN ('TODOS','RESPONSAVEIS') OR (c.publico = 'TURMA' AND c.id_turma IN "
                "(SELECT a.id_turma FROM aluno_responsavel ar JOIN aluno a ON a.id_aluno = ar.id_aluno "
                "WHERE ar.id_responsavel = ?)))"), [uid]
    # PROFESSOR: vê os gerais, os de professores, os das turmas em que leciona e os que ele mesmo publicou
    return ("(c.publico IN ('TODOS','PROFESSORES') OR c.id_usuario_autor = ? OR (c.publico = 'TURMA' AND c.id_turma IN "
            "(SELECT id_turma FROM turma_disciplina WHERE id_professor = ?)))"), [uid, uid]


def destinatarios_comunicado(publico: str, id_turma: int | None) -> list[int]:
    """Ids dos usuários ativos que devem ser notificados de um comunicado."""
    if publico == "TODOS":
        sql, p = "SELECT id_usuario FROM usuario WHERE ativo = 1", ()
    elif publico == "ALUNOS":
        sql, p = "SELECT id_usuario FROM usuario WHERE ativo = 1 AND perfil = 'ALUNO'", ()
    elif publico == "RESPONSAVEIS":
        sql, p = "SELECT id_usuario FROM usuario WHERE ativo = 1 AND perfil = 'RESPONSAVEL'", ()
    elif publico == "PROFESSORES":
        sql, p = "SELECT id_usuario FROM usuario WHERE ativo = 1 AND perfil = 'PROFESSOR'", ()
    else:  # TURMA: alunos da turma, seus responsáveis e os professores que lecionam nela
        sql = """SELECT u.id_usuario FROM usuario u WHERE u.ativo = 1 AND (
                   u.id_usuario IN (SELECT id_aluno FROM aluno WHERE id_turma = ?)
                OR u.id_usuario IN (SELECT ar.id_responsavel FROM aluno_responsavel ar JOIN aluno a ON a.id_aluno = ar.id_aluno WHERE a.id_turma = ?)
                OR u.id_usuario IN (SELECT id_professor FROM turma_disciplina WHERE id_turma = ?))"""
        p = (id_turma, id_turma, id_turma)
    return [r["id_usuario"] for r in rows(sql, p)]


def responsaveis_do_aluno(id_aluno: int) -> list[int]:
    return [r["id_responsavel"] for r in rows(
        "SELECT ar.id_responsavel FROM aluno_responsavel ar JOIN usuario u ON u.id_usuario = ar.id_responsavel "
        "WHERE ar.id_aluno = ? AND u.ativo = 1", (id_aluno,))]


def coordenadores() -> list[int]:
    return [r["id_usuario"] for r in rows("SELECT id_usuario FROM usuario WHERE ativo = 1 AND perfil = 'COORDENADOR'")]


def notificar(usuarios: list[int], tipo: str, titulo: str, mensagem: str, link: str | None = None, ignorar: int | None = None, con=None) -> int:
    """Cria uma notificação para cada usuário (sem repetir destinatários e sem notificar quem gerou o fato).
    Usa a conexão `con` quando chamada dentro de uma transação; do contrário confirma sozinha."""
    destino = sorted({u for u in usuarios if u != ignorar})
    if not destino:
        return 0
    c = con or get_db()
    c.executemany(
        "INSERT INTO notificacao (id_usuario, tipo, titulo, mensagem, link) VALUES (?,?,?,?,?)",
        [(u, tipo, titulo[:160], mensagem, link) for u in destino],
    )
    if con is None:
        c.commit()
    return len(destino)
