-- ============================================================================
-- Eduvance - Sistema Integrado de Gestão e Acompanhamento Educacional
-- Schema PostgreSQL (Sprint 03) - evolução do modelo relacional da Sprint 02
--
-- Ajustes em relação à Sprint 02 (documentados no relatório):
--   * turma_disciplina ganhou chave substituta id_turma_disciplina (+ UNIQUE turma/disciplina)
--   * usuario.perfil inclui ADMIN; usuario.ativo; índice único case-insensitive em e-mail
--   * avaliacao.bimestre (boletim por bimestre); avaliacao.peso (Sprint 04)
--   * ocorrencia.titulo
--   * material.detalhe / material.vestibular; forum.id_disciplina
--   * NOVAS tabelas: horario (PB22) e redacao (PB28)
--   * trigger: no máximo 2 responsáveis por aluno (requisito 6.1)
-- ============================================================================

-- ---------- Usuários e perfis ----------------------------------------------
CREATE TABLE usuario (
    id_usuario  SERIAL       PRIMARY KEY,
    nome        VARCHAR(120) NOT NULL,
    email       VARCHAR(160) NOT NULL,
    senha_hash  VARCHAR(100) NOT NULL,
    perfil      VARCHAR(20)  NOT NULL
                CHECK (perfil IN ('ADMIN','COORDENADOR','PROFESSOR','ALUNO','RESPONSAVEL')),
    ativo       BOOLEAN      NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_usuario_email ON usuario (lower(email));

CREATE TABLE turma (
    id_turma    SERIAL      PRIMARY KEY,
    nome        VARCHAR(60) NOT NULL,
    ano_letivo  INTEGER     NOT NULL,
    UNIQUE (nome, ano_letivo)
);

CREATE TABLE disciplina (
    id_disciplina SERIAL      PRIMARY KEY,
    nome          VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE aluno (
    id_aluno        INTEGER     PRIMARY KEY REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    matricula       VARCHAR(20) NOT NULL UNIQUE,
    data_nascimento DATE,
    serie           VARCHAR(40),
    id_turma        INTEGER     REFERENCES turma(id_turma) ON DELETE SET NULL
);
CREATE INDEX ix_aluno_turma ON aluno (id_turma);

CREATE TABLE responsavel (
    id_responsavel INTEGER     PRIMARY KEY REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    telefone       VARCHAR(30)
);

CREATE TABLE professor (
    id_professor  INTEGER      PRIMARY KEY REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    especialidade VARCHAR(80)
);

CREATE TABLE coordenador (
    id_coordenador INTEGER     PRIMARY KEY REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    cargo          VARCHAR(80)
);

CREATE TABLE aluno_responsavel (
    id_aluno         INTEGER NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    id_responsavel   INTEGER NOT NULL REFERENCES responsavel(id_responsavel) ON DELETE CASCADE,
    grau_parentesco  VARCHAR(40),
    PRIMARY KEY (id_aluno, id_responsavel)
);

CREATE FUNCTION fn_limite_responsaveis() RETURNS trigger AS $$
BEGIN
    IF (SELECT count(*) FROM aluno_responsavel WHERE id_aluno = NEW.id_aluno) >= 2 THEN
        RAISE EXCEPTION 'Um aluno pode ter no máximo 2 responsáveis vinculados'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_limite_responsaveis
    BEFORE INSERT ON aluno_responsavel
    FOR EACH ROW EXECUTE FUNCTION fn_limite_responsaveis();

-- ---------- Estrutura acadêmica ---------------------------------------------
CREATE TABLE turma_disciplina (
    id_turma_disciplina SERIAL  PRIMARY KEY,
    id_turma            INTEGER NOT NULL REFERENCES turma(id_turma) ON DELETE CASCADE,
    id_disciplina       INTEGER NOT NULL REFERENCES disciplina(id_disciplina) ON DELETE CASCADE,
    id_professor        INTEGER REFERENCES professor(id_professor) ON DELETE SET NULL,
    UNIQUE (id_turma, id_disciplina)
);
CREATE INDEX ix_td_professor ON turma_disciplina (id_professor);

CREATE TABLE horario (                      -- NOVA (PB22)
    id_horario          SERIAL      PRIMARY KEY,
    id_turma_disciplina INTEGER     NOT NULL REFERENCES turma_disciplina(id_turma_disciplina) ON DELETE CASCADE,
    dia_semana          SMALLINT    NOT NULL CHECK (dia_semana BETWEEN 1 AND 7), -- 1=segunda ... 7=domingo
    hora_inicio         TIME        NOT NULL,
    hora_fim            TIME        NOT NULL,
    sala                VARCHAR(20),
    CHECK (hora_fim > hora_inicio)
);

CREATE TABLE conteudo (
    id_conteudo         SERIAL       PRIMARY KEY,
    id_turma_disciplina INTEGER      NOT NULL REFERENCES turma_disciplina(id_turma_disciplina) ON DELETE CASCADE,
    titulo              VARCHAR(160) NOT NULL,
    descricao           TEXT,
    data_aula           DATE         NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE atividade (
    id_atividade        SERIAL       PRIMARY KEY,
    id_turma_disciplina INTEGER      NOT NULL REFERENCES turma_disciplina(id_turma_disciplina) ON DELETE CASCADE,
    titulo              VARCHAR(160) NOT NULL,
    descricao           TEXT,
    data_entrega        TIMESTAMPTZ  NOT NULL,
    criado_em           TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_atividade_td ON atividade (id_turma_disciplina);

CREATE TABLE entrega_atividade (
    id_entrega   SERIAL      PRIMARY KEY,
    id_atividade INTEGER     NOT NULL REFERENCES atividade(id_atividade) ON DELETE CASCADE,
    id_aluno     INTEGER     NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    status       VARCHAR(12) NOT NULL DEFAULT 'PENDENTE'
                 CHECK (status IN ('PENDENTE','ENTREGUE','CORRIGIDA')),
    nota         NUMERIC(4,2) CHECK (nota BETWEEN 0 AND 10),
    entregue_em  TIMESTAMPTZ,
    UNIQUE (id_atividade, id_aluno)
);

CREATE TABLE avaliacao (
    id_avaliacao        SERIAL       PRIMARY KEY,
    id_turma_disciplina INTEGER      NOT NULL REFERENCES turma_disciplina(id_turma_disciplina) ON DELETE CASCADE,
    titulo              VARCHAR(160) NOT NULL,
    data_avaliacao      DATE         NOT NULL,
    tipo                VARCHAR(30)  NOT NULL DEFAULT 'PROVA',
    bimestre            SMALLINT     NOT NULL DEFAULT 1 CHECK (bimestre BETWEEN 1 AND 4),
    peso                NUMERIC(3,1) NOT NULL DEFAULT 1 CHECK (peso > 0 AND peso <= 5)   -- Sprint 04: média ponderada
);
CREATE UNIQUE INDEX ux_avaliacao_titulo ON avaliacao (id_turma_disciplina, bimestre, lower(titulo));

CREATE TABLE nota (
    id_nota      SERIAL       PRIMARY KEY,
    id_avaliacao INTEGER      NOT NULL REFERENCES avaliacao(id_avaliacao) ON DELETE CASCADE,
    id_aluno     INTEGER      NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    valor        NUMERIC(4,2) NOT NULL CHECK (valor BETWEEN 0 AND 10),
    UNIQUE (id_avaliacao, id_aluno)
);

CREATE TABLE frequencia (
    id_frequencia       SERIAL  PRIMARY KEY,
    id_aluno            INTEGER NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    id_turma_disciplina INTEGER NOT NULL REFERENCES turma_disciplina(id_turma_disciplina) ON DELETE CASCADE,
    data                DATE    NOT NULL,
    presente            BOOLEAN NOT NULL,
    UNIQUE (id_aluno, id_turma_disciplina, data)
);

-- ---------- Comunicação e administração -------------------------------------
CREATE TABLE comunicado (
    id_comunicado    SERIAL       PRIMARY KEY,
    titulo           VARCHAR(160) NOT NULL,
    mensagem         TEXT         NOT NULL,
    data_publicacao  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    id_usuario_autor INTEGER      REFERENCES usuario(id_usuario) ON DELETE SET NULL
);

CREATE TABLE ocorrencia (
    id_ocorrencia   SERIAL       PRIMARY KEY,
    id_aluno        INTEGER      NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    id_professor    INTEGER      REFERENCES professor(id_professor) ON DELETE SET NULL,
    titulo          VARCHAR(160) NOT NULL,
    descricao       TEXT         NOT NULL,
    data_ocorrencia TIMESTAMPTZ  NOT NULL DEFAULT now(),
    status          VARCHAR(12)  NOT NULL DEFAULT 'ABERTA'
                    CHECK (status IN ('ABERTA','EM_ANALISE','RESOLVIDA'))
);

CREATE TABLE mensalidade (
    id_mensalidade  SERIAL        PRIMARY KEY,
    id_aluno        INTEGER       NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    valor           NUMERIC(10,2) NOT NULL CHECK (valor >= 0),
    vencimento      DATE          NOT NULL,
    status          VARCHAR(10)   NOT NULL DEFAULT 'ABERTA'
                    CHECK (status IN ('ABERTA','PAGA','ATRASADA')),
    forma_pagamento VARCHAR(30)
);

CREATE TABLE evento (
    id_evento SERIAL       PRIMARY KEY,
    titulo    VARCHAR(160) NOT NULL,
    descricao TEXT,
    inicio    TIMESTAMPTZ  NOT NULL,
    fim       TIMESTAMPTZ,
    tipo      VARCHAR(30)  NOT NULL DEFAULT 'GERAL'
);

-- ---------- Área de vestibular ----------------------------------------------
CREATE TABLE simulado (
    id_simulado    SERIAL       PRIMARY KEY,
    titulo         VARCHAR(160) NOT NULL,
    data_aplicacao DATE         NOT NULL,
    vestibular     VARCHAR(40)  NOT NULL
);

CREATE TABLE resultado_simulado (
    id_resultado SERIAL        PRIMARY KEY,
    id_simulado  INTEGER       NOT NULL REFERENCES simulado(id_simulado) ON DELETE CASCADE,
    id_aluno     INTEGER       NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    pontuacao    NUMERIC(6,1)  NOT NULL CHECK (pontuacao BETWEEN 0 AND 1000),
    percentual   NUMERIC(5,2)  NOT NULL CHECK (percentual BETWEEN 0 AND 100),
    UNIQUE (id_simulado, id_aluno)
);

CREATE TABLE redacao (                      -- NOVA (PB28)
    id_redacao   SERIAL       PRIMARY KEY,
    id_aluno     INTEGER      NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    tema         VARCHAR(200) NOT NULL,
    texto        TEXT         NOT NULL,
    nota         NUMERIC(6,1) CHECK (nota BETWEEN 0 AND 1000),
    id_professor INTEGER      REFERENCES professor(id_professor) ON DELETE SET NULL,
    status       VARCHAR(10)  NOT NULL DEFAULT 'ENVIADA' CHECK (status IN ('ENVIADA','CORRIGIDA')),
    enviada_em   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE material (
    id_material   SERIAL       PRIMARY KEY,
    titulo        VARCHAR(160) NOT NULL,
    tipo          VARCHAR(30)  NOT NULL,
    detalhe       VARCHAR(40),
    url           VARCHAR(300),
    vestibular    VARCHAR(40),
    id_disciplina INTEGER      REFERENCES disciplina(id_disciplina) ON DELETE SET NULL
);

CREATE TABLE forum (
    id_forum      SERIAL       PRIMARY KEY,
    titulo        VARCHAR(200) NOT NULL,
    descricao     TEXT,
    data_criacao  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    id_disciplina INTEGER      REFERENCES disciplina(id_disciplina) ON DELETE SET NULL
);

CREATE TABLE post_forum (
    id_post         SERIAL      PRIMARY KEY,
    id_forum        INTEGER     NOT NULL REFERENCES forum(id_forum) ON DELETE CASCADE,
    id_usuario      INTEGER     NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    conteudo        TEXT        NOT NULL,
    data_publicacao TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE recomendacao_ia (
    id_recomendacao SERIAL      PRIMARY KEY,
    id_aluno        INTEGER     NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    id_disciplina   INTEGER     REFERENCES disciplina(id_disciplina) ON DELETE SET NULL,
    tipo            VARCHAR(40) NOT NULL,
    justificativa   TEXT,
    criada_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
