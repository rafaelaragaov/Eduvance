# Eduvance — Sistema Integrado de Gestão e Acompanhamento Educacional

Plataforma que centraliza informações acadêmicas, pedagógicas e administrativas entre escola, professores, alunos e responsáveis, com uma área de preparação para vestibulares.

**Disciplina:** Fábrica de Software · **Turma:** 8NB · **Estado:** Sprint 04 — primeiro módulo completo (Notas, Frequência e Boletim)

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
cd backend && python -m unittest discover -s tests -v    # 43 testes de integração (banco temporário)
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

Próximas Sprints: agenda e calendário, comunicados, ocorrências, mensalidades, notificações, chat professor/aluno, gabaritos e serviço de recomendação (Python/FastAPI) — itens PB13 a PB30 do backlog.

## Equipe

Matheus Henrique da Costa Nascimento · Rafael Aragão Vieira · José Gabriel Rocha Barreto · Gabriel do Vale Alcoforado Braga
