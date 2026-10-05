# Eduvance — Sprint 03: Estrutura Inicial Funcionando

**Projeto:** Sistema Integrado de Gestão e Acompanhamento Educacional — Eduvance
**Grupo nº:** ___ · **Turma:** 8NB
**Integrantes:** Alexandre Rodrigues Aroeira Junior · Matheus Henrique da Costa Nascimento · Rafael Aragão Vieira · José Gabriel Rocha Barreto · Gabriel do Vale Alcoforado Braga
**Repositório:** https://github.com/rafaelaragaov/Eduvance

> Rascunho do texto do relatório (seção da Sprint 03). As figuras estão em `docs/evidencias/`.

---

## 1. Descrição da estrutura implementada

A Sprint 03 transforma o planejamento e a modelagem das Sprints 01 e 02 em um sistema executável, com back-end, banco de dados e interface web integrados.

| Camada | Implementação |
|---|---|
| Interface | React 19 + TypeScript; telas fiéis aos protótipos (login, dashboards de aluno, responsável, professor, coordenador e administrador, área de vestibular, cadastro de usuários, atividades) com layout responsivo (desktop e celular) |
| API REST | Python + Flask. Blueprints por módulo (`auth`, `usuarios`, `atividades`, `notas`, `dashboard`, `vestibular`, `catalogo`) e camada de serviços com as regras acadêmicas e de acesso |
| Segurança | Autenticação por JWT (validade de 8 h); senhas armazenadas como hash PBKDF2-SHA256 com *salt*; limite de tentativas de login; validação de entrada no servidor; cabeçalhos de segurança; o perfil é relido do banco a cada requisição |
| Banco de dados | SQLite com 27 tabelas (as 25 da Sprint 02 + `horario` e `redacao`), integridade referencial ativa, restrições `UNIQUE`/`CHECK` e gatilho que limita a 2 responsáveis por aluno |

Funcionalidades do backlog cobertas: PB01 (estrutura), PB02 (login), PB03 (permissões), PB04–PB06 (cadastros de aluno, responsável e professor), PB09 (dashboard), PB11 (lançamento de notas, em versão inicial), PB14–PB15 (atividades e controle de status) e parte de PB25/PB28/PB29 (simulados, redações e materiais na área de vestibular).

## 2. Banco de dados conectado

A aplicação abre o arquivo SQLite criado a partir do `schema.sql` da Sprint 02 (evoluído nesta Sprint) e consulta/grava nele em toda operação. O endpoint `GET /api/health` comprova a comunicação:

```
{ "status": "ok", "banco": "SQLite", "arquivo": "eduvance.db", "tabelas": 27, "usuarios": 120 }
```

Evidências: `evidencias/db_conexao.txt` (resposta do health-check, lista de tabelas, contagem por perfil e senhas armazenadas somente como hash).

## 3. Login, cadastro e controle de perfis

**Login** (`01_login.png`, `02_login_erro.png`): aceita e-mail ou matrícula + senha; credenciais inválidas retornam mensagem genérica (sem revelar se o usuário existe). Aluno entra por matrícula, conforme o requisito 6.1.

**Cadastro de usuários** (`13_cadastro_usuario_modal.png`, `14_usuarios_lista.png`): formulário com campos específicos por perfil (aluno: matrícula, turma, série, nascimento e até 2 responsáveis; responsável: telefone; professor: especialidade; coordenador: cargo). Validações: nome, e-mail, senha mínima, matrícula obrigatória para aluno, e-mail e matrícula únicos, máximo de 2 responsáveis. O teste de ponta a ponta cadastra um aluno pela interface e o faz entrar com a matrícula recém-criada.

**Controle de perfis** (matriz completa no README): o administrador gerencia todos os perfis; o coordenador gerencia apenas professores; o professor só atua nas turmas em que leciona; aluno e responsável têm acesso de leitura limitado aos próprios dados (o responsável, apenas aos alunos vinculados). Cada regra é aplicada no servidor e coberta por testes automatizados; a interface também bloqueia rotas não permitidas (`Acesso restrito`).

## 4. CRUD principal funcionando — Atividades

Entidade escolhida: **Atividade** (PB14/PB15), por ser o ponto de contato entre professor, aluno e responsável.

| Operação | Evidência |
|---|---|
| Cadastrar | formulário "Nova Atividade / Tarefa" do dashboard do professor e modal "Nova atividade" (`05_dash_professor.png`, `09_crud_lista_professor.png`) |
| Consultar | lista com busca, prazo, prioridade (Urgente/Pendente/Planejado) e entregas (`09_crud_lista_professor.png`, `15_atividades_aluno.png`) |
| Atualizar | modal de edição (`10_crud_editar_modal.png`); a alteração permanece após recarregar a página, provando a persistência |
| Excluir | confirmação antes de excluir (`12_crud_excluir_confirma.png`) |
| Validação | mensagens do servidor no formulário (`11_crud_validacao.png`) |

Regras de negócio: o professor só cria/edita/exclui atividades de turmas e disciplinas em que leciona (tentativas indevidas retornam 403); coordenador e administrador gerenciam todas; o aluno marca/desfaz a entrega; o responsável apenas consulta.

## 5. Procedimento de execução local

Pré-requisitos: Python 3.11+ e Node.js 18+.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.init_db                                  # cria o banco com dados de demonstração
cd ../frontend && npm install && npm run build         # compila a interface
cd ../backend && python run.py                         # http://localhost:5000
```

Contas de demonstração e demais opções estão no `README.md`. Testes automatizados: `cd backend && python -m unittest discover -s tests -v` — 27 testes, todos aprovados (`evidencias/testes_backend.txt`).

## 6. Repositório GitHub

https://github.com/rafaelaragaov/Eduvance — contém `backend/`, `frontend/`, `database/`, `docs/` e `README.md`.
*(Atenção: as Sprints 01 e 02 citam `https://github.com/Aroeiraa/Eduvance`; registrar a mudança do endereço no documento consolidado.)*

## 7. Ajustes no planejamento e na modelagem (com justificativa)

| Ajuste | Justificativa |
|---|---|
| **Stack:** Flask (Python) no lugar de Spring Boot (Java) | Foi escolhida uma stack que a equipe pudesse executar e testar de ponta a ponta nesta Sprint, com configuração mínima (um `pip install`). A arquitetura em camadas, o padrão REST/JSON, JWT + hash de senha e o RBAC definidos na Sprint 02 foram mantidos. Python já estava previsto para o serviço de recomendação (FastAPI). |
| **Banco:** SQLite em vez de PostgreSQL nesta Sprint | A Sprint 02 entregou o banco em SQLite (`eduvance.db`) e a Sprint 03 pede conexão com esse banco. Mantido o `schema.postgresql.sql`, validado em PostgreSQL 16, para a migração futura. |
| `turma_disciplina` com chave substituta `id_turma_disciplina` | Simplifica as FKs de atividade, avaliação, frequência, horário e conteúdo, que referenciam a combinação turma+disciplina; mantida `UNIQUE (id_turma, id_disciplina)`. |
| Novas tabelas `horario` e `redacao` | Necessárias para a agenda do dia/cronograma (PB22) e para "Redações Enviadas" da área de vestibular (PB28), exibidas nos protótipos. |
| Novos atributos: `avaliacao.bimestre`, `ocorrencia.titulo`, `material.detalhe/vestibular`, `forum.id_disciplina`, `usuario.ativo`, perfil `ADMIN` | Exigidos pelas telas (boletim por bimestre, título da ocorrência, duração/tamanho do material, fórum por disciplina) e pelo caso de uso do administrador. |
| Gatilho "máx. 2 responsáveis por aluno" | Garante no banco o requisito 6.1 da Sprint 01. |

## 8. Dificuldades encontradas

- Os protótipos têm pequenas inconsistências entre telas (turma e horários de uma mesma aula diferem entre os perfis). Os dados de demonstração foram padronizados para ficarem coerentes entre si.
- Datas e prazos "relativos" (hoje, amanhã) exigiram dados de demonstração gerados em relação ao dia da execução.
- Definir quem pode cadastrar o quê (administrador × coordenador) a partir dos requisitos da Sprint 01.

## 9. Próximos passos

1. Boletim completo e histórico (PB10) e registro de frequência (PB12).
2. Agenda escolar, calendário de provas e calendário letivo (PB13, PB16, PB17).
3. Comunicados, ocorrências e notificações (PB18, PB19, PB21) e mensalidades (PB20).
4. Gerenciamento de horários (PB22), chat professor/aluno (PB24), gabaritos e explicações (PB26, PB27).
5. Migração para PostgreSQL e serviço de recomendação em Python/FastAPI (arquitetura da Sprint 02).
6. Testes de interface automatizados e *deploy* em servidor.
