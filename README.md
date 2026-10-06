# Eduvance — Sistema Integrado de Gestão e Acompanhamento Educacional

Plataforma que centraliza informações acadêmicas, pedagógicas e administrativas entre escola, professores, alunos e responsáveis, com uma área de preparação para vestibulares.

**Disciplina:** Fábrica de Software · **Turma:** 8NB · **Estado:** Sprint 05 — segundo módulo (Comunicação Escolar: Comunicados, Ocorrências e Notificações)

| Camada | Tecnologia |
|---|---|
| Interface | React 19 + TypeScript (build com esbuild) |
| API REST | Python 3 + Flask, autenticação JWT, senhas com hash PBKDF2-SHA256 |
| Banco de dados | SQLite (`database/schema.sql`) — script equivalente para PostgreSQL em `database/schema.postgresql.sql` |

## O que está funcionando (Sprint 03)

- ✅ **Banco conectado** — a API usa o banco criado na Sprint 02; `GET /api/health` comprova a conexão.
- ✅ **Login** por e-mail **ou matrícula** (aluno) + senha, integrado ao banco, com bloqueio de força bruta.
- ✅ **Cadastro de usuários** (alunos, responsáveis, professores, coordenadores, administradores) com persistência e validações.
- ✅ **Controle de perfis (RBAC)** no servidor e na interface — ver matriz abaixo.
- ✅ **CRUD principal: Atividades** (cadastrar, consultar, atualizar, excluir) + entrega pelo aluno.
- ✅ **Dashboards por perfil** conforme os protótipos (aluno, responsável, professor, coordenador, admin) e **Área de Vestibular**.
- ✅ **Execução local** em um comando.

## Modo escuro

Todas as telas têm tema claro e escuro. O botão de lua/sol fica na barra lateral (no celular, no topo) e na tela de login. A escolha é salva no navegador (`localStorage`, chave `eduvance:tema`); sem escolha salva, o sistema segue o tema do sistema operacional. O tema é aplicado antes da primeira pintura, então não há "flash" de tela clara. As cores são variáveis CSS em `frontend/src/styles.css` (bloco `:root[data-theme='dark']`) e a lógica está em `frontend/src/theme.tsx`. Evidências e roteiro de teste: `docs/evidencias/dark-mode/`.

## Sprint 05 — Módulo Comunicação Escolar (PB18, PB19, PB21)

1. **Coordenação, administração e professores** publicam **comunicados** para todos, só alunos, só responsáveis, só professores ou uma turma (professor: apenas turmas em que leciona). Cada destinatário é **notificado** e marca como lido; quem publicou vê "lido por X de Y".
2. **Professor** registra uma **ocorrência** (disciplinar, pedagógica, saúde ou elogio; leve, média ou grave). A coordenação é notificada (e os responsáveis, se média/grave ou elogio).
3. **Coordenação** coloca em análise e **resolve com parecer obrigatório**; a situação só avança e cada passo fica no **histórico**. Professor e responsáveis são avisados.
4. **Sino de notificações** no cabeçalho (contador, lista rápida e central em `/notificacoes`). Integra com o módulo anterior: quando a frequência de um aluno cai abaixo de 75%, aluno e responsáveis recebem um alerta (uma única vez).

Regras: público do comunicado não muda depois de publicado; comunicado repetido em 5 min é recusado; ocorrência duplicada no mesmo dia é recusada; elogio não tem gravidade; ocorrência resolvida não pode ser editada; aluno vê só as próprias ocorrências e responsável só as dos filhos.

> Atualizando da Sprint 04? Recrie o banco: `python -m app.init_db --reset` (novas tabelas `comunicado_leitura`, `ocorrencia_historico`, `notificacao` e novas colunas em `comunicado` e `ocorrencia`).

## Sprint 04 — Módulo Notas, Frequência e Boletim (PB10, PB11, PB12)

Fluxo completo e persistido no banco:

1. **Professor** cadastra uma **avaliação** (prova, trabalho, teste ou projeto, com bimestre e peso) — menu *Avaliações*.
2. **Lança as notas** de toda a turma de uma vez, com validação por aluno — menu *Lançar Notas*.
3. **Registra a chamada** do dia, com acumulado de faltas e alerta de frequência abaixo de 75% — menu *Frequência*.
4. **Aluno** e **responsável** (e coordenação/admin/professor, conforme o escopo) consultam o **boletim**: média ponderada por bimestre, média parcial, frequência e situação (Aprovado, Recuperação, Reprovado por faltas) — menu *Boletim*.

Validações e regras: título/tipo/bimestre/peso/data (dentro do ano letivo) nas avaliações; título único por bimestre; nota de 0 a 10 (aceita vírgula); chamada só em dia útil, sem data futura e com todos os alunos da turma; avaliação com notas não pode ser excluída. Erros do servidor aparecem junto ao campo ou em mensagens claras na tela.

> Atualizando da Sprint 03? Recrie o banco: `python -m app.init_db --reset` (a tabela `avaliacao` ganhou a coluna `peso`).

## Como executar localmente

Pré-requisitos: **Python 3.11+** e **Node.js 18+** (o Node só é usado para compilar o front-end).

```bash
# 1) Back-end: dependências e banco de dados (cria database/eduvance.db com dados de demonstração)
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.init_db              # use --reset para recriar o banco do zero

# 2) Front-end: compilar
cd ../frontend
npm install
npm run build

# 3) Subir o sistema (API + interface)
cd ../backend
python run.py
```

Abra **http://localhost:5000**.

### Contas de demonstração

| Perfil | Login | Senha |
|---|---|---|
| Aluno (Lucas Silva) | matrícula `<ano>0001` (ex.: `20260001`) | `senha123` |
| Responsável (Maria Silva) | `maria@eduvance.com` | `senha123` |
| Professor (Ricardo Ramos) | `ricardo@eduvance.com` | `senha123` |
| Coordenadora (Paula Ramos) | `paula@eduvance.com` | `senha123` |
| Administrador | `admin@eduvance.com` | `admin123` |

> Estas contas existem apenas para demonstração. Para ocultar o painel de contas na tela de login, compile com `EDUVANCE_DEMO=0 npm run build`.

### Variáveis de ambiente (opcionais)

| Variável | Padrão | Uso |
|---|---|---|
| `EDUVANCE_DB` | `database/eduvance.db` | caminho do arquivo SQLite |
| `EDUVANCE_JWT_SECRET` | valor de desenvolvimento | **defina em produção** |
| `EDUVANCE_JWT_HORAS` | `8` | validade do token |
| `PORT` | `5000` | porta do servidor |

### Desenvolvimento

```bash
cd frontend && npm run watch                      # recompila o front-end ao salvar
cd backend && EDUVANCE_DEBUG=1 python run.py      # API com recarga automática
```

### Testes

```bash
cd backend && python -m unittest discover -s tests -v    # 60 testes de integração (banco temporário)
```

## Controle de perfis

| Recurso | Admin | Coordenador | Professor | Aluno | Responsável |
|---|:-:|:-:|:-:|:-:|:-:|
| Cadastrar/editar/excluir usuários | todos os perfis | **somente professores** | — | — | — |
| Atividades (CRUD) | todas | todas | **só das suas turmas** | consulta + marca entrega | consulta (aluno vinculado) |
| Avaliações (CRUD) | ✔ | ✔ | só das suas turmas | — | — |
| Lançar notas | ✔ | ✔ | só das suas turmas | — | — |
| Registrar frequência | ✔ | ✔ | só das suas turmas | — | — |
| Boletim completo | qualquer aluno | qualquer aluno | alunos das suas turmas | o próprio | apenas filhos vinculados |
| Dashboard | geral | institucional | turmas/aulas | pessoal | alunos vinculados |
| Área de Vestibular | — | — | — | ✔ | — |
| Boletim/mensalidades de um aluno | ✔ | ✔ | alunos das suas turmas | o próprio | apenas filhos vinculados |

As regras são aplicadas **no servidor** (decorator `@auth_required(...)` + verificações de escopo) e refletidas na interface.

## API (resumo)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/health` | conexão com o banco |
| POST | `/api/auth/login` | login por e-mail/matrícula → JWT |
| GET | `/api/auth/me` | usuário autenticado |
| GET/POST | `/api/usuarios` | listar / cadastrar |
| GET/PUT/DELETE | `/api/usuarios/{id}` | consultar / atualizar / excluir |
| GET/POST | `/api/atividades` | listar / cadastrar |
| GET/PUT/DELETE | `/api/atividades/{id}` | consultar / atualizar / excluir |
| PUT | `/api/atividades/{id}/entrega` | aluno marca entrega |
| GET/POST | `/api/avaliacoes` | listar / cadastrar avaliações |
| GET/PUT/DELETE | `/api/avaliacoes/{id}` | consultar / atualizar / excluir |
| GET/PUT | `/api/notas/avaliacao/{id}` | notas da turma / gravar todas de uma vez (atômico) |
| GET/PUT | `/api/frequencia` | chamada do dia / registrar chamada |
| GET | `/api/boletim/{idAluno}` | boletim completo (por bimestre, média, frequência, situação) |
| GET/POST | `/api/comunicados` | listar (filtros `lido=nao`, `busca`) / publicar |
| GET/PUT/DELETE | `/api/comunicados/{id}` | detalhe (autor vê leituras) / editar / excluir |
| PUT | `/api/comunicados/{id}/lido` | marcar como lido · `GET /api/comunicados/nao-lidos` |
| GET/POST | `/api/ocorrencias` | listar (filtros `status`, `gravidade`, `tipo`, `idAluno`, `busca`) / registrar |
| GET/PUT/DELETE | `/api/ocorrencias/{id}` | detalhe com histórico / editar / excluir |
| PUT | `/api/ocorrencias/{id}/status` | coordenação: em análise ou resolver (parecer) · `GET /api/ocorrencias/resumo` |
| GET | `/api/notificacoes` | minhas notificações (`naoLidas=1`) · `GET /api/notificacoes/contagem` |
| PUT/DELETE | `/api/notificacoes/{id}/lida` · `/lidas` · `/{id}` | marcar lida / marcar todas / excluir |
| GET | `/api/catalogo/alunos` | alunos que o usuário pode consultar |
| PUT | `/api/notas` | lançamento rápido de uma nota (dashboard do professor) |
| GET | `/api/dashboard` | dashboard do perfil logado |
| GET | `/api/alunos/{id}/resumo` | boletim, mensalidades e ocorrências |
| GET/POST | `/api/vestibular` | simulados, redações, fórum, materiais |

## Estrutura do repositório

```
backend/            API Flask (app/), testes (tests/), run.py
  app/routes/       auth, usuarios, atividades, avaliacoes, notas, frequencia, boletim, dashboard, vestibular, catalogo
  app/services/     regras acadêmicas e de acesso
  app/seed.py       dados de demonstração
frontend/           React + TypeScript (src/), build.mjs
database/           schema.sql (SQLite) · schema.postgresql.sql (migração)
docs/               relatório da Sprint 03 e evidências (capturas de tela)
```

## Roadmap

Próximas Sprints: agenda e calendário (PB13, PB16, PB17), mensalidades (PB20), horários (PB22), chat professor/aluno, gabaritos e serviço de recomendação (Python/FastAPI) — itens PB13 a PB30 do backlog.

## Equipe

Matheus Henrique da Costa Nascimento · Rafael Aragão Vieira · José Gabriel Rocha Barreto · Gabriel do Vale Alcoforado Braga
