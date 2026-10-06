# Eduvance — Sprint 04: Primeiro Módulo Completo

**Módulo entregue:** Notas, Frequência e Boletim (PB10, PB11 e PB12 do Product Backlog)
**Repositório:** https://github.com/rafaelaragaov/Eduvance · **Turma:** 8NB
**Integrantes:** Matheus Henrique da Costa Nascimento · Rafael Aragão Vieira · José Gabriel Rocha Barreto · Gabriel do Vale Alcoforado Braga

> O relatório em PDF (com as Sprints 01 a 04) é montado a partir deste conteúdo e das capturas em `docs/evidencias/sprint04/`.

## Fluxo do módulo

1. O **professor** cadastra uma avaliação (`/avaliacoes`): título, tipo, bimestre, data, peso, turma/disciplina.
2. **Lança as notas** da turma inteira (`/notas/{id}`), com validação por aluno.
3. **Registra a chamada** do dia (`/frequencia`) e vê o acumulado de faltas.
4. **Aluno / responsável / coordenação** consultam o **boletim** (`/boletim`, `/boletim/{idAluno}`): média ponderada por bimestre, média parcial, frequência e situação.

## Entregáveis da Sprint

| Item | Como foi atendido |
|---|---|
| Módulo totalmente funcional | fluxo avaliação → notas → frequência → boletim, integrado entre telas e API |
| Persistência | SQLite; testes automáticos e de navegador recarregam a página e reiniciam o servidor (`evidencias/sprint04/db_persistencia.txt`) |
| Validações | formulário no navegador + servidor (campos, formatos, limites e regras de negócio) |
| Mensagens de erro | erro por campo, alertas na tela e mensagens de regra (409/403/400) |
| Navegação | menus por perfil, links entre dashboard, avaliações, notas, frequência e boletim; rotas com parâmetros |
| Commits organizados | um commit por funcionalidade (`git log --oneline`) |

## Regras de negócio

- Nota de 0 a 10 (aceita vírgula); `valor` vazio remove a nota; a gravação em lote é **atômica** (se uma linha for inválida, nada é salvo).
- Média do bimestre = média ponderada pelo peso das avaliações; média parcial = média dos bimestres com nota; aprovação com média ≥ 6,0.
- Frequência mínima de 75%: com ao menos 10 aulas registradas, abaixo disso a situação é "Reprovado por faltas".
- Chamada: só em dia útil, sem data futura, com **todos** os alunos da turma informados; corrigir a chamada atualiza (não duplica).
- Avaliação com notas lançadas não pode ser excluída nem trocada de turma; título único por bimestre/turma/disciplina; data dentro do ano letivo da turma.

## Ajustes na modelagem (justificados)

| Ajuste | Justificativa |
|---|---|
| `avaliacao.peso` (padrão 1) | média ponderada no boletim (provas e trabalhos com pesos diferentes) |
| índice único `(turma/disciplina, bimestre, título)` | impede avaliações duplicadas; reforça a regra também no banco |
| parâmetros `FREQUENCIA_MINIMA` e `MIN_AULAS_PARA_FALTA` | regra de reprovação por faltas configurável sem mexer no código |
| seed com Prova B1 e Trabalho B1 | demonstrar o boletim por bimestre |

## Testes

`cd backend && python -m unittest discover -s tests -v` — **43 testes** (27 das Sprints anteriores + 16 do módulo), todos aprovados (`evidencias/sprint04/testes_backend_sprint04.txt`).
