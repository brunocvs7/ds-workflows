# ds-workflows

Política de CI e de proteção de branch compartilhada por todos os projetos de DS.
Não é uma CLI: os projetos **referenciam** este repo e o GitHub busca os workflows daqui.

| O quê | Onde | Como é usado |
|---|---|---|
| CI reutilizável (lint, test, conformance, branch-name) | `.github/workflows/python-ci.yml` | `uses:` no `ci.yml` de cada projeto |
| Verificações de conformidade (`ds-check`) | `src/ds_conformance/` | o CI roda via `uvx --from git+...@v1 ds-check` |
| Proteção da `main` | `rulesets/protect-main.json` | aplicado por `scripts/protect-repo.sh` |

## Usando em um projeto

`.github/workflows/ci.yml` do projeto (já vem no `ds-project-template`):

```yaml
on:
  pull_request:
  push:
    branches: [main]
jobs:
  ci:                      # o nome PRECISA ser `ci`
    uses: brunocvs7/ds-workflows/.github/workflows/python-ci.yml@v1
    # with:
    #   run-conformance: false          # para repos que não são projetos DS
    #   branch-pattern: '^(feature|fix)/.+$'
```

Proteja a `main` do repo (uma vez):

```bash
./scripts/protect-repo.sh brunocvs7/meu-projeto
```

Ruleset aplicado: exige PR, exige os checks `ci / lint`, `ci / test`, `ci / conformance` e
`ci / branch-name` verdes e atualizados com a `main`, bloqueia push direto, force-push e deleção.
Merge só por squash. 0 aprovações exigidas (dá para subir quando houver mais pessoas).

> Conta pessoal: rulesets só são aplicados em repos **públicos** no plano Free (privados exigem Pro).
> Em uma organização no plano Team, este JSON pode virar um ruleset de organização com
> alvo `ds-*`, dispensando o script.

## Jobs do CI

| Job | O que faz |
|---|---|
| `lint` | `pre-commit run --all-files` com o `.pre-commit-config.yaml` do projeto |
| `test` | `uv sync --locked` + `pytest --cov` |
| `conformance` | `deptry` (dependências declaradas) + `ds-check` |
| `branch-name` | em PRs para a `main`, a branch de origem precisa ser `<tipo>/<descricao>` com tipo em `feature, fix, hotfix, refactor, experiment, docs, chore, test, ci` |

## ds-check

```bash
uvx --from git+https://github.com/brunocvs7/ds-workflows@v1 ds-check [caminho]
```

| Verificação | Falha quando |
|---|---|
| estrutura de pastas | falta `data/{raw,interim,processed,external}`, `models`, `notebooks`, `reports/figures`, `tests`, `pyproject.toml`, `uv.lock` ou `.pre-commit-config.yaml`; ou `src/` não tem exatamente um pacote |
| sem dados/modelos no git | há arquivos versionados em `data/` ou `models/` além de `.gitkeep` |
| notebooks | nome fora de `NN-iniciais-descricao.ipynb` ou notebook com outputs |
| teste para cada módulo | `src/<pkg>/x.py` sem `tests/test_x.py` |
| sem caminhos absolutos | strings com `/Users/`, `/home/` ou `C:\` em `src/` |
| contrato do pipeline | `<pkg>.pipelines.train` e `.predict` não rodam sobre `tests/fixtures/sample_raw.csv`, não geram `model.joblib`, `metrics.json`, `predictions.csv`, ou duas execuções com a mesma seed dão métricas diferentes |

## Versionamento

Os projetos apontam para a tag `v1`. Para publicar uma mudança compatível:

```bash
git tag -f v1 && git push -f origin v1
```

Mudança que quebra projetos existentes (ex.: nova verificação obrigatória): crie `v2` e migre os
projetos quando estiverem prontos.

## Desenvolvimento

```bash
uv sync && uv run pytest && uv run ruff check .
```
