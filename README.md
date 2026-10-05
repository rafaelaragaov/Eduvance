# Eduvance — Sistema Integrado de Gestão e Acompanhamento Educacional

Plataforma que centraliza informações acadêmicas, pedagógicas e administrativas entre escola, professores, alunos e responsáveis, com uma área de preparação para vestibulares.

**Disciplina:** Fábrica de Software · **Turma:** 8NB · **Estado:** Sprint 03 — estrutura inicial funcionando

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
cd backend && python -m unittest discover -s tests -v    # 27 testes de integração (banco temporário)
```

## Controle de perfis

| Recurso | Admin | Coordenador | Professor | Aluno | Responsável |
|---|:-:|:-:|:-:|:-:|:-:|
| Cadastrar/editar/excluir usuários | todos os perfis | **somente professores** | — | — | — |
| Atividades (CRUD) | todas | todas | **só das suas turmas** | consulta + marca entrega | consulta (aluno vinculado) |
| Lançar notas | ✔ | ✔ | só das suas turmas | — | — |
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
| GET/PUT | `/api/notas/...` | lançamento de notas |
| GET | `/api/dashboard` | dashboard do perfil logado |
| GET | `/api/alunos/{id}/resumo` | boletim, mensalidades e ocorrências |
| GET/POST | `/api/vestibular` | simulados, redações, fórum, materiais |

## Estrutura do repositório

```
backend/            API Flask (app/), testes (tests/), run.py
  app/routes/       auth, usuarios, atividades, notas, dashboard, vestibular, catalogo
  app/services/     regras acadêmicas e de acesso
  app/seed.py       dados de demonstração
frontend/           React + TypeScript (src/), build.mjs
database/           schema.sql (SQLite) · schema.postgresql.sql (migração)
docs/               relatório da Sprint 03 e evidências (capturas de tela)
```

## Roadmap

Próximas Sprints: boletim completo, frequência, agenda e calendário, comunicados, ocorrências, mensalidades, notificações, chat professor/aluno, gabaritos e serviço de recomendação (Python/FastAPI) — itens PB10 a PB30 do backlog.

## Equipe

Alexandre Rodrigues Aroeira Junior · Matheus Henrique da Costa Nascimento · Rafael Aragão Vieira · José Gabriel Rocha Barreto · Gabriel do Vale Alcoforado Braga
