-- ============================================================================
-- Eduvance - Sistema Integrado de Gestão e Acompanhamento Educacional
-- Schema SQLite (Sprint 03) - evolução do schema.sql entregue na Sprint 02.
-- (Versão equivalente para PostgreSQL: database/schema.postgresql.sql)
--
-- Ajustes em relação à Sprint 02 (documentados no relatório):
--   * turma_disciplina ganhou chave substituta id_turma_disciplina (+ UNIQUE turma/disciplina)
--   * usuario.perfil inclui ADMIN; usuario.ativo; e-mail único sem diferenciar maiúsculas
--   * avaliacao.bimestre (boletim por bimestre); avaliacao.peso (Sprint 04); ocorrencia.titulo
--   * material.detalhe / material.vestibular; forum.id_disciplina
--   * NOVAS tabelas: horario (PB22) e redacao (PB28)
--   * trigger: no máximo 2 responsáveis por aluno (requisito 6.1)
--   * Sprint 05 (módulo Comunicação Escolar): comunicado.publico/id_turma; ocorrencia.tipo/gravidade/parecer/
--     resolvida_em; NOVAS tabelas comunicado_leitura, ocorrencia_historico e notificacao
-- Datas/horas são gravadas como texto ISO-8601 no horário local da escola.
-- ============================================================================
PRAGMA foreign_keys = ON;

-- ---------- Usuários e perfis ----------------------------------------------
CREATE TABLE usuario (
    id_usuario  INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    senha_hash  TEXT    NOT NULL,
    perfil      TEXT    NOT NULL
                CHECK (perfil IN ('ADMIN','COORDENADOR','PROFESSOR','ALUNO','RESPONSAVEL')),
    ativo       INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
    criado_em   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE turma (
    id_turma    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    ano_letivo  INTEGER NOT NULL,
    UNIQUE (nome, ano_letivo)
);

CREATE TABLE disciplina (
    id_disciplina INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT    NOT NULL UNIQUE
);

CREATE TABLE aluno (
    id_aluno        INTEGER PRIMARY KEY REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    matricula       TEXT    NOT NULL UNIQUE,
    data_nascimento TEXT,
    serie           TEXT,
    id_turma        INTEGER REFERENCES turma(id_turma) ON DELETE SET NULL
);
CREATE INDEX ix_aluno_turma ON aluno (id_turma);

CREATE TABLE responsavel (
    id_responsavel INTEGER PRIMARY KEY REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    telefone       TEXT
);

CREATE TABLE professor (
    id_professor  INTEGER PRIMARY KEY REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    especialidade TEXT
);

CREATE TABLE coordenador (
    id_coordenador INTEGER PRIMARY KEY REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    cargo          TEXT
);

CREATE TABLE aluno_responsavel (
    id_aluno         INTEGER NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    id_responsavel   INTEGER NOT NULL REFERENCES responsavel(id_responsavel) ON DELETE CASCADE,
    grau_parentesco  TEXT,
    PRIMARY KEY (id_aluno, id_responsavel)
);

CREATE TRIGGER trg_limite_responsaveis
BEFORE INSERT ON aluno_responsavel
WHEN (SELECT count(*) FROM aluno_responsavel WHERE id_aluno = NEW.id_aluno) >= 2
BEGIN
    SELECT RAISE(ABORT, 'Um aluno pode ter no máximo 2 responsáveis vinculados');
END;

-- ---------- Estrutura acadêmica ---------------------------------------------
CREATE TABLE turma_disciplina (
    id_turma_disciplina INTEGER PRIMARY KEY AUTOINCREMENT,
    id_turma            INTEGER NOT NULL REFERENCES turma(id_turma) ON DELETE CASCADE,
    id_disciplina       INTEGER NOT NULL REFERENCES disciplina(id_disciplina) ON DELETE CASCADE,
    id_professor        INTEGER REFERENCES professor(id_professor) ON DELETE SET NULL,
    UNIQUE (id_turma, id_disciplina)
);
CREATE INDEX ix_td_professor ON turma_disciplina (id_professor);

CREATE TABLE horario (                      -- NOVA (PB22)
    id_horario          INTEGER PRIMARY KEY AUTOINCREMENT,
    id_turma_disciplina INTEGER NOT NULL REFERENCES turma_disciplina(id_turma_disciplina) ON DELETE CASCADE,
    dia_semana          INTEGER NOT NULL CHECK (dia_semana BETWEEN 1 AND 7), -- 1=segunda ... 7=domingo
    hora_inicio         TEXT    NOT NULL,   -- HH:MM
    hora_fim            TEXT    NOT NULL,   -- HH:MM
    sala                TEXT,
    CHECK (hora_fim > hora_inicio)
);

CREATE TABLE conteudo (
    id_conteudo         INTEGER PRIMARY KEY AUTOINCREMENT,
    id_turma_disciplina INTEGER NOT NULL REFERENCES turma_disciplina(id_turma_disciplina) ON DELETE CASCADE,
    titulo              TEXT    NOT NULL,
    descricao           TEXT,
    data_aula           TEXT    NOT NULL DEFAULT (date('now','localtime'))
);

CREATE TABLE atividade (
    id_atividade        INTEGER PRIMARY KEY AUTOINCREMENT,
    id_turma_disciplina INTEGER NOT NULL REFERENCES turma_disciplina(id_turma_disciplina) ON DELETE CASCADE,
    titulo              TEXT    NOT NULL,
    descricao           TEXT,
    data_entrega        TEXT    NOT NULL,   -- YYYY-MM-DDTHH:MM:SS
    criado_em           TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX ix_atividade_td ON atividade (id_turma_disciplina);

CREATE TABLE entrega_atividade (
    id_entrega   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_atividade INTEGER NOT NULL REFERENCES atividade(id_atividade) ON DELETE CASCADE,
    id_aluno     INTEGER NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    status       TEXT    NOT NULL DEFAULT 'PENDENTE' CHECK (status IN ('PENDENTE','ENTREGUE','CORRIGIDA')),
    nota         REAL    CHECK (nota BETWEEN 0 AND 10),
    entregue_em  TEXT,
    UNIQUE (id_atividade, id_aluno)
);

CREATE TABLE avaliacao (
    id_avaliacao        INTEGER PRIMARY KEY AUTOINCREMENT,
    id_turma_disciplina INTEGER NOT NULL REFERENCES turma_disciplina(id_turma_disciplina) ON DELETE CASCADE,
    titulo              TEXT    NOT NULL,
    data_avaliacao      TEXT    NOT NULL,
    tipo                TEXT    NOT NULL DEFAULT 'PROVA',
    bimestre            INTEGER NOT NULL DEFAULT 1 CHECK (bimestre BETWEEN 1 AND 4),
    peso                REAL    NOT NULL DEFAULT 1 CHECK (peso > 0 AND peso <= 5)   -- Sprint 04: média ponderada
);
-- Sprint 04: não permite duas avaliações com o mesmo título no mesmo bimestre da turma/disciplina
CREATE UNIQUE INDEX ux_avaliacao_titulo ON avaliacao (id_turma_disciplina, bimestre, titulo COLLATE NOCASE);

CREATE TABLE nota (
    id_nota      INTEGER PRIMARY KEY AUTOINCREMENT,
    id_avaliacao INTEGER NOT NULL REFERENCES avaliacao(id_avaliacao) ON DELETE CASCADE,
    id_aluno     INTEGER NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    valor        REAL    NOT NULL CHECK (valor BETWEEN 0 AND 10),
    UNIQUE (id_avaliacao, id_aluno)
);

CREATE TABLE frequencia (
    id_frequencia       INTEGER PRIMARY KEY AUTOINCREMENT,
    id_aluno            INTEGER NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    id_turma_disciplina INTEGER NOT NULL REFERENCES turma_disciplina(id_turma_disciplina) ON DELETE CASCADE,
    data                TEXT    NOT NULL,
    presente            INTEGER NOT NULL CHECK (presente IN (0,1)),
    UNIQUE (id_aluno, id_turma_disciplina, data)
);

-- ---------- Comunicação e administração -------------------------------------
CREATE TABLE comunicado (
    id_comunicado    INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo           TEXT NOT NULL,
    mensagem         TEXT NOT NULL,
    data_publicacao  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    id_usuario_autor INTEGER REFERENCES usuario(id_usuario) ON DELETE SET NULL,
    publico          TEXT NOT NULL DEFAULT 'TODOS'
                     CHECK (publico IN ('TODOS','ALUNOS','RESPONSAVEIS','PROFESSORES','TURMA')),
    id_turma         INTEGER REFERENCES turma(id_turma) ON DELETE CASCADE,
    CHECK ((publico = 'TURMA') = (id_turma IS NOT NULL))      -- turma só quando o público é TURMA
);

CREATE TABLE comunicado_leitura (                              -- NOVA (Sprint 05)
    id_comunicado INTEGER NOT NULL REFERENCES comunicado(id_comunicado) ON DELETE CASCADE,
    id_usuario    INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    lido_em       TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (id_comunicado, id_usuario)
);

CREATE TABLE ocorrencia (
    id_ocorrencia   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_aluno        INTEGER NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    id_professor    INTEGER REFERENCES professor(id_professor) ON DELETE SET NULL,
    titulo          TEXT NOT NULL,
    descricao       TEXT NOT NULL,
    data_ocorrencia TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    status          TEXT NOT NULL DEFAULT 'ABERTA' CHECK (status IN ('ABERTA','EM_ANALISE','RESOLVIDA')),
    tipo            TEXT NOT NULL DEFAULT 'DISCIPLINAR' CHECK (tipo IN ('DISCIPLINAR','PEDAGOGICA','SAUDE','ELOGIO')),
    gravidade       TEXT NOT NULL DEFAULT 'LEVE' CHECK (gravidade IN ('LEVE','MEDIA','GRAVE')),
    parecer         TEXT,                                      -- conclusão da coordenação (obrigatória ao resolver)
    resolvida_em    TEXT
);

CREATE TABLE ocorrencia_historico (                            -- NOVA (Sprint 05): trilha de auditoria
    id_historico    INTEGER PRIMARY KEY AUTOINCREMENT,
    id_ocorrencia   INTEGER NOT NULL REFERENCES ocorrencia(id_ocorrencia) ON DELETE CASCADE,
    id_usuario      INTEGER REFERENCES usuario(id_usuario) ON DELETE SET NULL,
    status_anterior TEXT,
    status_novo     TEXT NOT NULL,
    comentario      TEXT,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE notificacao (                                     -- NOVA (Sprint 05)
    id_notificacao INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario     INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    tipo           TEXT NOT NULL CHECK (tipo IN ('COMUNICADO','OCORRENCIA','FREQUENCIA')),
    titulo         TEXT NOT NULL,
    mensagem       TEXT NOT NULL,
    link           TEXT,
    lida           INTEGER NOT NULL DEFAULT 0 CHECK (lida IN (0,1)),
    criada_em      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX ix_notificacao_usuario ON notificacao (id_usuario, lida, criada_em);

CREATE TABLE mensalidade (
    id_mensalidade  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_aluno        INTEGER NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    valor           REAL    NOT NULL CHECK (valor >= 0),
    vencimento      TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'ABERTA' CHECK (status IN ('ABERTA','PAGA','ATRASADA')),
    forma_pagamento TEXT
);

CREATE TABLE evento (
    id_evento INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo    TEXT NOT NULL,
    descricao TEXT,
    inicio    TEXT NOT NULL,
    fim       TEXT,
    tipo      TEXT NOT NULL DEFAULT 'GERAL'
);

-- ---------- Área de vestibular ----------------------------------------------
CREATE TABLE simulado (
    id_simulado    INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo         TEXT NOT NULL,
    data_aplicacao TEXT NOT NULL,
    vestibular     TEXT NOT NULL
);

CREATE TABLE resultado_simulado (
    id_resultado INTEGER PRIMARY KEY AUTOINCREMENT,
    id_simulado  INTEGER NOT NULL REFERENCES simulado(id_simulado) ON DELETE CASCADE,
    id_aluno     INTEGER NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    pontuacao    REAL    NOT NULL CHECK (pontuacao BETWEEN 0 AND 1000),
    percentual   REAL    NOT NULL CHECK (percentual BETWEEN 0 AND 100),
    UNIQUE (id_simulado, id_aluno)
);

CREATE TABLE redacao (                      -- NOVA (PB28)
    id_redacao   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_aluno     INTEGER NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    tema         TEXT    NOT NULL,
    texto        TEXT    NOT NULL,
    nota         REAL    CHECK (nota BETWEEN 0 AND 1000),
    id_professor INTEGER REFERENCES professor(id_professor) ON DELETE SET NULL,
    status       TEXT    NOT NULL DEFAULT 'ENVIADA' CHECK (status IN ('ENVIADA','CORRIGIDA')),
    enviada_em   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE material (
    id_material   INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo        TEXT NOT NULL,
    tipo          TEXT NOT NULL,
    detalhe       TEXT,
    url           TEXT,
    vestibular    TEXT,
    id_disciplina INTEGER REFERENCES disciplina(id_disciplina) ON DELETE SET NULL
);

CREATE TABLE forum (
    id_forum      INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo        TEXT NOT NULL,
    descricao     TEXT,
    data_criacao  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    id_disciplina INTEGER REFERENCES disciplina(id_disciplina) ON DELETE SET NULL
);

CREATE TABLE post_forum (
    id_post         INTEGER PRIMARY KEY AUTOINCREMENT,
    id_forum        INTEGER NOT NULL REFERENCES forum(id_forum) ON DELETE CASCADE,
    id_usuario      INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    conteudo        TEXT NOT NULL,
    data_publicacao TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE recomendacao_ia (
    id_recomendacao INTEGER PRIMARY KEY AUTOINCREMENT,
    id_aluno        INTEGER NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    id_disciplina   INTEGER REFERENCES disciplina(id_disciplina) ON DELETE SET NULL,
    tipo            TEXT NOT NULL,
    justificativa   TEXT,
    criada_em       TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
