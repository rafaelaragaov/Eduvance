# Como contribuir com o Eduvance

Este guia existe para que o histórico do GitHub mostre **quem fez o quê e quando** (correção pedida na avaliação da Sprint 04).
Vale para todos os integrantes do grupo.

## 1. Identidade nos commits (obrigatório)

Cada pessoa commita **com o próprio nome e e-mail**, na própria máquina. Nada de conta compartilhada ("Equipe Eduvance").

```bash
git config user.name  "Seu Nome Completo"
git config user.email "o-mesmo-email-cadastrado-no-github@exemplo.com"   # senão o GitHub não associa ao seu perfil
git config commit.template .gitmessage                                    # modelo de mensagem deste repositório
```

Conferir: `git log -3 --format='%an <%ae> %ad %s'` deve mostrar o seu nome.
Trabalho feito em dupla leva `Co-authored-by: Nome <email>` no fim da mensagem.

## 2. Fluxo de trabalho: uma branch por funcionalidade

```
main  ←  Pull Request (revisado por outra pessoa)  ←  feature/<pb>-<resumo-curto>
```

1. `git switch main && git pull`
2. `git switch -c feature/pb16-calendario-de-provas` (prefixos: `feature/`, `fix/`, `docs/`, `test/`, `chore/`)
3. Commits pequenos e frequentes, um por unidade lógica (ver §3). **Não** acumule o trabalho de uma sprint em um único dia.
4. `git push -u origin feature/pb16-calendario-de-provas` e abra o Pull Request usando o modelo `.github/pull_request_template.md`.
5. Outra pessoa do grupo revisa (comentários no PR) e só então faz o *merge*. Quem escreveu não aprova o próprio PR.
6. Depois do merge, apague a branch.

Antes de abrir o PR, rode os testes: `cd backend && python -m unittest discover -s tests` (e `cd ../recomendacao && python -m unittest discover -s tests -t ..`).

## 3. Mensagens de commit

Formato: `tipo(escopo): resumo no imperativo, até ~72 caracteres`, em português.

| tipo | quando |
|---|---|
| `feat` | funcionalidade nova (`feat(api): remarcação de avaliação com aviso à turma`) |
| `fix` | correção de defeito |
| `test` | testes e roteiros de evidência |
| `docs` | README, relatórios, comentários |
| `refactor` / `chore` | reorganização sem mudar comportamento / manutenção |

Escopos usados: `api`, `web`, `db`, `recomendacao`, `docs`.
O corpo da mensagem (opcional) explica o **porquê**; referencie o item do backlog (`PB16`) quando houver.

## 4. Quem fez o quê

A tabela de responsabilidades por sprint fica em [`docs/CONTRIBUICOES.md`](docs/CONTRIBUICOES.md) e deve ser preenchida
pelo próprio grupo. O script abaixo gera, a partir do Git, o resumo de commits por pessoa e por dia (use no relatório):

```bash
python tools/contribuicoes.py                # tudo
python tools/contribuicoes.py --desde 2026-10-01
```

## 5. O que não entra no repositório

Bancos `.db`, `node_modules/`, `frontend/dist/`, ambientes virtuais, senhas e chaves reais (use variáveis de ambiente — ver README).
