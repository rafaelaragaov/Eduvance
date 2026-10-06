# Eduvance — Sprint 05: Segundo Módulo Funcionando

**Módulo entregue:** Comunicação Escolar — Comunicados (PB18), Ocorrências (PB19) e Notificações (PB21)
**Repositório:** https://github.com/rafaelaragaov/Eduvance · **Turma:** 8NB
**Integrantes:** Matheus Henrique da Costa Nascimento · Rafael Aragão Vieira · José Gabriel Rocha Barreto · Gabriel do Vale Alcoforado Braga

> O relatório em PDF (Sprints 01 a 05) é montado a partir deste conteúdo e das capturas em `docs/evidencias/sprint05/`.

## Fluxo do módulo

1. Coordenação/professor **publica um comunicado** (`/comunicados`) para um público; os destinatários são notificados.
2. O destinatário lê e **marca como lido**; quem publicou acompanha "lido por X de Y".
3. O professor **registra uma ocorrência** (`/ocorrencias`); a coordenação é notificada.
4. A coordenação **analisa e resolve com parecer**; professor e responsáveis são avisados; tudo fica no histórico.
5. O **sino** e a página `/notificacoes` reúnem os avisos de comunicados, ocorrências e frequência.

## Regras de negócio (novas ou atualizadas)

| Regra | Situação |
|---|---|
| Comunicado tem público (todos, alunos, responsáveis, professores ou turma); cada perfil só vê o que lhe cabe | nova |
| Professor publica apenas para turmas em que leciona; coordenação/admin para qualquer público | nova |
| Público não muda depois de publicado; só autor, coordenação ou admin editam/excluem | nova |
| Mesmo comunicado (autor, título, público) em até 5 min é recusado (409) | nova |
| Ocorrência: título 3–120, descrição 10–2000, tipo e gravidade válidos; elogio só com gravidade leve; data não futura | nova |
| Ocorrência duplicada (aluno + título + dia) é recusada (409) | nova |
| Situação só avança: ABERTA → EM_ANALISE → RESOLVIDA; resolver exige parecer (≥ 10 caracteres); resolvida não é editada | nova |
| Média/grave e elogio também notificam os responsáveis; resolução notifica professor e responsáveis | nova |
| Frequência abaixo de 75% (com ≥ 10 aulas) notifica aluno e responsáveis uma única vez, na transição | atualizada (módulo 1) |
| "Ocorrências em aberto" do dashboard passou a contar também as "em análise" | atualizada |
| Comunicados do dashboard do aluno respeitam o público | atualizada |
| Alerta "abaixo do mínimo" na chamada só vale com ≥ 10 aulas (igual ao boletim) | corrigida |

## Testes

- Backend: `cd backend && python -m unittest discover -s tests -v` → **60 testes** (43 anteriores + 17 do módulo).
- Navegador: roteiro `docs/evidencias/sprint05/roteiro_e2e.mjs` (Playwright) → **44 verificações** aprovadas; regressões das Sprints 03 e 04 reexecutadas.
- Esquema PostgreSQL validado em PostgreSQL 16.

## Bugs encontrados e corrigidos

| # | Bug | Como foi achado | Correção |
|---|---|---|---|
| 1 | Mensagem "Ocorrência não encontrado" (concordância; também em Avaliação e Atividade desde a Sprint 04) | revisão da captura do teste de navegador | `nao_encontrado(..., feminino=True)` + teste |
| 2 | Rótulo "Em análises" no resumo de ocorrências | revisão da captura | rótulo plural por situação |
| 3 | KPI "Ocorrências em aberto" ignorava "em análise" (teste existente falhou: 3 ≠ 4) | teste de regressão | regra atualizada no dashboard |
| 4 | Chamada marcava aluno "abaixo do mínimo" com 1 aula (boletim exigia 10) e geraria alerta falso | revisão do código ao criar o alerta | mesma regra nos dois lugares + teste |
| 5 | Datas `AAAA-MM-DD HH:MM:SS` do SQLite não são lidas pelo Safari | revisão do código | `parse()` troca o espaço por `T` |
| 6 | Roteiro de navegador da Sprint 03 oscila (1 em 4 execuções): verifica sem esperar a lista recarregar | regressão | pendente: trocar por espera explícita |

Pendências: rodar `npm run typecheck` na máquina do grupo (o pacote de tipos do React estava bloqueado no ambiente de desenvolvimento); notificações são internas (sem e-mail/push); `git push` para o GitHub feito pelo grupo.
