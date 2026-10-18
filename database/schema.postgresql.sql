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
--   * Sprint 05 (Comunicação Escolar): comunicado.publico/id_turma; ocorrencia.tipo/gravidade/parecer/resolvida_em;
--     NOVAS tabelas comunicado_leitura, ocorrencia_historico e notificacao (validado no PostgreSQL 16)
--   Sprint 06 (migração real): colunas lógicas (ativo, presente, lida, dia_inteiro) são SMALLINT 0/1 e datas/horas TIMESTAMP
--     sem fuso, exatamente como a aplicação as trata no SQLite — o mesmo código roda nos dois bancos (ver backend/app/db.py).
--   Sprint 06: evento (publico, id_turma, autor, dia_inteiro, tipos controlados), notificacao.tipo AGENDA + chave,
--     NOVA tabela preferencia_usuario
-- ============================================================================

-- ---------- Usuários e perfis ----------------------------------------------
CREATE TABLE usuario (
    id_usuario  SERIAL       PRIMARY KEY,
    nome        VARCHAR(120) NOT NULL,
    email       VARCHAR(160) NOT NULL,
    senha_hash  VARCHAR(255) NOT NULL,
    perfil      VARCHAR(20)  NOT NULL
                CHECK (perfil IN ('ADMIN','COORDENADOR','PROFESSOR','ALUNO','RESPONSAVEL')),
    ativo        SMALLINT      NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
    criado_em   TIMESTAMP  NOT NULL DEFAULT localtimestamp(0)
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
    data_entrega        TIMESTAMP  NOT NULL,
    criado_em           TIMESTAMP  NOT NULL DEFAULT localtimestamp(0)
);
CREATE INDEX ix_atividade_td ON atividade (id_turma_disciplina);

CREATE TABLE entrega_atividade (
    id_entrega   SERIAL      PRIMARY KEY,
    id_atividade INTEGER     NOT NULL REFERENCES atividade(id_atividade) ON DELETE CASCADE,
    id_aluno     INTEGER     NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    status       VARCHAR(12) NOT NULL DEFAULT 'PENDENTE'
                 CHECK (status IN ('PENDENTE','ENTREGUE','CORRIGIDA')),
    nota         NUMERIC(4,2) CHECK (nota BETWEEN 0 AND 10),
    entregue_em  TIMESTAMP,
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
    presente             SMALLINT NOT NULL CHECK (presente IN (0,1)),
    UNIQUE (id_aluno, id_turma_disciplina, data)
);

-- ---------- Comunicação e administração -------------------------------------
CREATE TABLE comunicado (
    id_comunicado    SERIAL       PRIMARY KEY,
    titulo           VARCHAR(160) NOT NULL,
    mensagem         TEXT         NOT NULL,
    data_publicacao  TIMESTAMP  NOT NULL DEFAULT localtimestamp(0),
    id_usuario_autor INTEGER      REFERENCES usuario(id_usuario) ON DELETE SET NULL,
    publico          VARCHAR(14)  NOT NULL DEFAULT 'TODOS'
                     CHECK (publico IN ('TODOS','ALUNOS','RESPONSAVEIS','PROFESSORES','TURMA')),
    id_turma         INTEGER      REFERENCES turma(id_turma) ON DELETE CASCADE,
    CHECK ((publico = 'TURMA') = (id_turma IS NOT NULL))
);

CREATE TABLE comunicado_leitura (                -- NOVA (Sprint 05)
    id_comunicado INTEGER     NOT NULL REFERENCES comunicado(id_comunicado) ON DELETE CASCADE,
    id_usuario    INTEGER     NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    lido_em       TIMESTAMP NOT NULL DEFAULT localtimestamp(0),
    PRIMARY KEY (id_comunicado, id_usuario)
);

CREATE TABLE ocorrencia (
    id_ocorrencia   SERIAL       PRIMARY KEY,
    id_aluno        INTEGER      NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    id_professor    INTEGER      REFERENCES professor(id_professor) ON DELETE SET NULL,
    titulo          VARCHAR(160) NOT NULL,
    descricao       TEXT         NOT NULL,
    data_ocorrencia TIMESTAMP  NOT NULL DEFAULT localtimestamp(0),
    status          VARCHAR(12)  NOT NULL DEFAULT 'ABERTA'
                    CHECK (status IN ('ABERTA','EM_ANALISE','RESOLVIDA')),
    tipo            VARCHAR(12)  NOT NULL DEFAULT 'DISCIPLINAR'
                    CHECK (tipo IN ('DISCIPLINAR','PEDAGOGICA','SAUDE','ELOGIO')),
    gravidade       VARCHAR(5)   NOT NULL DEFAULT 'LEVE' CHECK (gravidade IN ('LEVE','MEDIA','GRAVE')),
    parecer         TEXT,
    resolvida_em    TIMESTAMP
);

CREATE TABLE ocorrencia_historico (              -- NOVA (Sprint 05)
    id_historico    SERIAL      PRIMARY KEY,
    id_ocorrencia   INTEGER     NOT NULL REFERENCES ocorrencia(id_ocorrencia) ON DELETE CASCADE,
    id_usuario      INTEGER     REFERENCES usuario(id_usuario) ON DELETE SET NULL,
    status_anterior VARCHAR(12),
    status_novo     VARCHAR(12) NOT NULL,
    comentario      TEXT,
    criado_em       TIMESTAMP NOT NULL DEFAULT localtimestamp(0)
);

CREATE TABLE notificacao (                       -- NOVA (Sprint 05)
    id_notificacao SERIAL       PRIMARY KEY,
    id_usuario     INTEGER      NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    tipo           VARCHAR(12)  NOT NULL CHECK (tipo IN ('COMUNICADO','OCORRENCIA','FREQUENCIA','AGENDA')),
    titulo         VARCHAR(160) NOT NULL,
    mensagem       TEXT         NOT NULL,
    link           VARCHAR(120),
    lida            SMALLINT      NOT NULL DEFAULT 0 CHECK (lida IN (0,1)),
    criada_em      TIMESTAMP  NOT NULL DEFAULT localtimestamp(0),
    chave          VARCHAR(80)                           -- Sprint 06: lembretes automáticos (evita repetir)
);
CREATE INDEX ix_notificacao_usuario ON notificacao (id_usuario, lida, criada_em);
CREATE UNIQUE INDEX ux_notificacao_chave ON notificacao (id_usuario, chave) WHERE chave IS NOT NULL;

CREATE TABLE mensalidade (
    id_mensalidade  SERIAL        PRIMARY KEY,
    id_aluno        INTEGER       NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    valor           NUMERIC(10,2) NOT NULL CHECK (valor >= 0),
    vencimento      DATE          NOT NULL,
    status          VARCHAR(10)   NOT NULL DEFAULT 'ABERTA'
                    CHECK (status IN ('ABERTA','PAGA','ATRASADA')),
    forma_pagamento VARCHAR(30)
);

CREATE TABLE evento (                                -- Sprint 06: calendário escolar (PB17)
    id_evento        SERIAL       PRIMARY KEY,
    titulo           VARCHAR(160) NOT NULL,
    descricao        TEXT,
    inicio           TIMESTAMP  NOT NULL,
    fim              TIMESTAMP,
    tipo             VARCHAR(12)  NOT NULL DEFAULT 'EVENTO'
                     CHECK (tipo IN ('EVENTO','REUNIAO','CONSELHO','FERIADO','RECESSO')),
    dia_inteiro       SMALLINT      NOT NULL DEFAULT 0 CHECK (dia_inteiro IN (0,1)),
    publico          VARCHAR(14)  NOT NULL DEFAULT 'TODOS'
                     CHECK (publico IN ('TODOS','ALUNOS','RESPONSAVEIS','PROFESSORES','TURMA')),
    id_turma         INTEGER REFERENCES turma(id_turma) ON DELETE CASCADE,
    id_usuario_autor INTEGER REFERENCES usuario(id_usuario) ON DELETE SET NULL,
    criado_em        TIMESTAMP  NOT NULL DEFAULT localtimestamp(0),
    CHECK ((publico = 'TURMA') = (id_turma IS NOT NULL)),
    CHECK (fim IS NULL OR fim >= inicio)
);
CREATE INDEX ix_evento_inicio ON evento (inicio);

CREATE TABLE preferencia_usuario (                   -- NOVA (Sprint 06): página Configurações
    id_usuario    INTEGER     PRIMARY KEY REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    fonte         INTEGER     NOT NULL DEFAULT 100 CHECK (fonte IN (85,100,115,130,150)),
    tema          VARCHAR(6)  NOT NULL DEFAULT 'auto' CHECK (tema IN ('claro','escuro','auto')),
    atualizada_em TIMESTAMP NOT NULL DEFAULT localtimestamp(0)
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
    enviada_em   TIMESTAMP  NOT NULL DEFAULT localtimestamp(0)
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
    data_criacao  TIMESTAMP  NOT NULL DEFAULT localtimestamp(0),
    id_disciplina INTEGER      REFERENCES disciplina(id_disciplina) ON DELETE SET NULL
);

CREATE TABLE post_forum (
    id_post         SERIAL      PRIMARY KEY,
    id_forum        INTEGER     NOT NULL REFERENCES forum(id_forum) ON DELETE CASCADE,
    id_usuario      INTEGER     NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    conteudo        TEXT        NOT NULL,
    data_publicacao TIMESTAMP NOT NULL DEFAULT localtimestamp(0)
);

CREATE TABLE recomendacao_ia (
    id_recomendacao SERIAL      PRIMARY KEY,
    id_aluno        INTEGER     NOT NULL REFERENCES aluno(id_aluno) ON DELETE CASCADE,
    id_disciplina   INTEGER     REFERENCES disciplina(id_disciplina) ON DELETE SET NULL,
    tipo            VARCHAR(40) NOT NULL CHECK (tipo IN ('REFORCO','PROVA','FREQUENCIA','ATIVIDADE','DESTAQUE')),
    prioridade      VARCHAR(10) NOT NULL DEFAULT 'MEDIA' CHECK (prioridade IN ('ALTA','MEDIA','BAIXA')),
    score           NUMERIC(5,1) NOT NULL DEFAULT 0,
    titulo          VARCHAR(160) NOT NULL DEFAULT '',
    justificativa   TEXT,                -- mensagem exibida ao aluno
    motivo          TEXT,                -- JSON com os números que originaram a sugestão (explicabilidade)
    link            VARCHAR(80),
    origem          VARCHAR(10) NOT NULL DEFAULT 'motor',   -- 'servico' (FastAPI) | 'motor' (embutido)
    criada_em       TIMESTAMP NOT NULL DEFAULT localtimestamp(0)
);
CREATE INDEX ix_recomendacao_aluno ON recomendacao_ia (id_aluno, score DESC);
