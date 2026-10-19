# Eduvance — Sprint 06: Terceiro Módulo, Integração e Ajustes

**Módulo entregue:** Agenda e Calendário Escolar — Agenda (PB13), Calendário de Provas (PB16) e Calendário Escolar (PB17)
**Repositório:** https://github.com/rafaelaragaov/Eduvance · **Turma:** 8NB
**Integrantes:** Matheus Henrique da Costa Nascimento · Rafael Aragão Vieira · José Gabriel Rocha Barreto · Gabriel do Vale Alcoforado Braga
**Grupo:** Eduvance

> O relatório em PDF (Sprints 01 a 06 + Sprint 06) é montado a partir deste conteúdo e das evidências em `docs/evidencias/sprint06/`. Só o Scrum Master o entrega.

## 1. Correções da Pré-Banca

> **Pendente de informação do grupo.** As observações da Pré-Banca ainda não foram repassadas e não serão inventadas. Preencha a tabela e o PDF é regerado.

| Nº | Observação da banca | Ação tomada | Situação | Evidência |
|---|---|---|---|---|
| 1 | _(colar a observação)_ | | | |

### Apontamentos do professor já tratados nesta Sprint (feedback das Sprints 03 e 04)

| Apontamento | O que foi feito | Situação | Evidência |
|---|---|---|---|
| Identificação do grupo e divergência de integrantes (Alexandre) | Composição atual documentada em `docs/CONTRIBUICOES.md`; PDFs antigos não reescritos, nota de esclarecimento na capa do consolidado | **Corrigido** | `docs/CONTRIBUICOES.md` |
| Roteiro E2E da Sprint 03 instável | Trocadas as esperas fixas por esperas explícitas; 17/17 estável | Corrigido | `docs/evidencias/sprint03/roteiro_e2e_resultado.txt` |
| Mostrar `npm run typecheck` real | Executado no PC do grupo em 18/10/2026 por `verificar.bat`: `tsc --noEmit` com código de saída 0, sem erros (a checagem parcial do ambiente de desenvolvimento foi substituída) | Corrigido | `verificacao_pc.txt` |
| Manter testes dos módulos anteriores | Suíte única: 111 testes; roteiros de navegador das Sprints 03, 05 e do modo escuro reexecutados | Corrigido | `testes_backend_*.txt`, `roteiro_e2e_resultado*.txt` |
| Histórico do GitHub concentrado/sem autoria | `CONTRIBUTING.md`, modelo de commit e de PR, `tools/contribuicoes.py` e `docs/CONTRIBUICOES.md` | **Processo definido; adoção é do grupo** | `CONTRIBUTING.md` |
| Avançar a migração real para PostgreSQL | Camada de banco dupla (SQLite/PostgreSQL), `docker-compose.yml`, `migrar_para_postgres.py`; suíte completa passa também no PostgreSQL 16 | Corrigido | `migracao_postgres.txt`, `testes_backend_postgres.txt` |
| Implementar o serviço de recomendação (FastAPI) | `recomendacao/` (motor + API FastAPI) integrado ao Flask, com plano B embutido | Corrigido (no PC do grupo: FastAPI 0.146.0, 18/18 testes e serviço no ar respondendo `/health` e `/recomendar`) | `verificacao_pc.txt`, `testes_recomendacao.txt` |

## 2. Terceiro módulo: Agenda e Calendário Escolar

Fluxo principal demonstrável:

1. **Coordenação** cadastra um evento no calendário (reunião, conselho, feriado, recesso, evento) para um público; os destinatários são **notificados**.
2. **Professor** vê as avaliações das suas turmas e **remarca** uma prova informando o motivo; a turma é **notificada** e a agenda é atualizada.
3. **Aluno** e **responsável** veem a **agenda** (aulas, atividades, provas e eventos), o **calendário de provas** e o **calendário escolar**; o dashboard mostra os próximos compromissos.
4. O sistema gera **lembretes** (sino de notificações) para prova e atividade próximas, sem repetir.
5. A **recomendação de estudo** cruza as provas da agenda com as médias do boletim.

Regras de negócio: feriado/recesso bloqueiam aula e avaliação naquele dia; no máximo 2 provas por dia por turma; avaliação com notas lançadas não pode ser remarcada; intervalo de consulta de até 100 dias; evento repetido é recusado; cada perfil só vê o que lhe cabe.

| Rota | Descrição |
|---|---|
| `GET /api/agenda` · `/proximos` · `/provas` | agenda por período · próximos compromissos · calendário de provas |
| `GET/POST /api/eventos`, `GET/PUT/DELETE /api/eventos/{id}` | calendário escolar (coordenação/admin escrevem) |
| `PATCH /api/avaliacoes/{id}/data` | remarcar avaliação (motivo obrigatório, notifica a turma) |
| `GET/PUT/DELETE /api/preferencias` | tamanho da fonte e tema por conta |
| `GET /api/recomendacoes?idAluno=` | recomendações de estudo (aluno, responsável, professor, coordenação) |

## 3. Integração entre módulos

| De → Para | Como |
|---|---|
| Notas/Avaliações → Agenda | provas e prazos aparecem na agenda e no calendário; remarcar atualiza ambos |
| Agenda → Comunicação | evento criado/remarcado/cancelado e lembretes geram notificações (tipo `AGENDA`) |
| Notas + Frequência + Agenda → Recomendação | o motor cruza média, queda, faltas e provas próximas |
| Todos → Dashboards | os cinco dashboards mostram compromissos; aluno e responsável mostram recomendações |
| Preferências → Interface | fonte e tema valem em todas as telas e acompanham a conta entre aparelhos |

## 4. Melhorias de interface

- **Configurações** (`/configuracoes`): tamanho da fonte em 5 níveis (85% a 150%), tema claro/escuro/automático, pré-visualização e "restaurar padrão". Todo o CSS usa `rem`, então o texto, os campos e os botões crescem juntos.
- Compromissos com cor por tipo e destaque de "hoje"/"amanhã"; cartões de recomendação com prioridade e justificativa.
- Link para o conteúdo (`Ir para o conteúdo`), foco visível, `aria-pressed` e rótulos nos botões de ícone.
- Compromissos e recomendações são clicáveis e levam à tela do item; estados vazios com texto de orientação.

## 5. Ajustes de navegação

- Menus por perfil reorganizados; **Agenda**, **Provas** e **Calendário Escolar** em todos os perfis aplicáveis.
- Itens do backlog ainda não implementados aparecem com a etiqueta **"Em breve"** em vez de levar a páginas vazias.
- **Configurações** fixa na barra lateral e no menu "Mais" do celular; o título da aba muda por página.
- Cartões dos dashboards e notificações do sino levam direto à tela do item (prova, evento, ocorrência).

## 6. Banco de dados: PostgreSQL de verdade

- `backend/app/db.py` escolhe o banco por `EDUVANCE_DATABASE_URL` (PostgreSQL) ou `EDUVANCE_DB` (SQLite). As consultas usam `?` e são traduzidas, então **o mesmo código roda nos dois**.
- `docker-compose.yml` sobe o PostgreSQL 16; `python -m app.migrar_para_postgres` copia o SQLite existente e **confere linha a linha** (31 tabelas, 1.291 linhas).
- Diferenças tratadas: `IS NOT ?` → `IS DISTINCT FROM`, parâmetros nulos tipados, `date()` no lugar de `substr` em timestamps, `ON CONFLICT DO NOTHING`.

## 7. Serviço de recomendação

`recomendacao/motor.py` (regras explicáveis) + `recomendacao/servico.py` (FastAPI: `GET /health`, `POST /recomendar`). Se `EDUVANCE_RECOMENDACAO_URL` estiver definido o Flask chama o serviço; se não estiver ou se ele cair, usa o motor embutido (`origem: motor` / `motor-fallback`) e a tela continua funcionando. O resultado é guardado em `recomendacao_ia`. Regras: reforço por média baixa ou queda, prova em até 7 dias × média, frequência, atividade a vencer/atrasada e destaque (média ≥ 9). Prioridade ALTA/MÉDIA/BAIXA e no máximo 6 itens.

## 8. Testes

| Suíte | Resultado |
|---|---|
| Backend (SQLite) — `python -m unittest discover -s tests` | **111 testes**, OK (3 pulados: dependem de PostgreSQL ou do dia da semana) |
| Backend (PostgreSQL 16) — `EDUVANCE_TEST_PG_URL=...` | **111 testes**, OK |
| Motor de recomendação + API FastAPI (PC do grupo) | 18 testes, OK (os 4 da camada FastAPI rodaram no PC; no ambiente de desenvolvimento eram pulados) |
| `npm run typecheck` e `npm run build` (PC do grupo) | código de saída 0 nos dois |
| Navegador — Sprint 06 (SQLite e PostgreSQL) | **54/54** em cada |
| Regressão de navegador: Sprint 03 · Sprint 05 · modo escuro | 17/17 · todas OK · todas OK |

Bugs encontrados nesta Sprint: diferenças de SQL entre SQLite e PostgreSQL (comparações com NULL, tipos de parâmetro, funções de data, tamanho do hash de senha); expectativas de testes antigos que mudaram de propósito (botão de tema agora alterna o que está visível; lembretes de agenda entram na contagem de notificações); espera instável no roteiro da Sprint 03 (corrigida).

## 9. Limitações e dificuldades

- O ambiente de desenvolvimento não alcança o PyPI nem o pacote `@types/react`: o FastAPI e o `npm run typecheck` oficiais só puderam ser executados no PC do grupo (`verificar.bat`), o que exigiu ler a saída por arquivo.
- Conciliar dois bancos em um único conjunto de consultas exigiu rever cada `IS`, `substr` e parâmetro nulo.
- Calendário × notas: manter uma única fonte (a avaliação) para a agenda, a prova e a nota, sem duplicar datas.
- Autoria dos commits: o histórico antigo não será reescrito.

## 10. Próximos passos

Mensalidades (PB20) e horários (PB22), chat professor/aluno (PB24), simulados e gabaritos da área de vestibular, notificações por e-mail, publicação em servidor com PostgreSQL gerenciado e CI com `typecheck` e testes a cada Pull Request.

## 11. Como executar

```bash
iniciar.bat                         # Windows: prepara tudo e abre http://localhost:5000
verificar.bat                       # Windows: typecheck + testes + serviço, grava docs/evidencias/sprint06/verificacao_pc.txt
docker compose up -d db             # PostgreSQL opcional (ver README)
```
