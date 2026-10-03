"""Verificações de conformidade: cada check recebe a raiz do projeto e retorna erros."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

REQUIRED_DIRS = [
    "data/raw",
    "data/interim",
    "data/processed",
    "data/external",
    "models",
    "notebooks",
    "reports/figures",
    "tests",
]
NOTEBOOK_NAME = re.compile(r"^\d{2}-[a-z]+-[a-z0-9-]+\.ipynb$")
ABSOLUTE_PATH = re.compile(r"""["'](/Users/|/home/|[A-Za-z]:\\)""")
SAMPLE_FIXTURE = "tests/fixtures/sample_raw.csv"
MODULES_WITHOUT_TESTS = {"__init__", "__main__"}


def find_package(root: Path) -> Path | None:
    """Retorna o único pacote em src/ (o nome é livre, para permitir renomear)."""
    src = root / "src"
    if not src.is_dir():
        return None
    packages = [p for p in src.iterdir() if (p / "__init__.py").is_file()]
    return packages[0] if len(packages) == 1 else None


def _git_files(root: Path, *paths: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", *paths], cwd=root, capture_output=True, text=True, check=True
    )
    return [line for line in out.stdout.splitlines() if line]


def check_structure(root: Path) -> list[str]:
    errors = [f"pasta obrigatória ausente: {d}/" for d in REQUIRED_DIRS if not (root / d).is_dir()]
    if find_package(root) is None:
        errors.append("src/ deve conter exatamente um pacote Python (pasta com __init__.py)")
    for f in ("pyproject.toml", "uv.lock", ".pre-commit-config.yaml"):
        if not (root / f).is_file():
            errors.append(f"arquivo obrigatório ausente: {f}")
    return errors


def check_no_committed_data(root: Path) -> list[str]:
    tracked = _git_files(root, "data", "models")
    return [
        f"arquivo de dados/modelo versionado no git: {f}"
        for f in tracked
        if Path(f).name != ".gitkeep"
    ]


def check_notebooks(root: Path) -> list[str]:
    errors = []
    for nb in sorted((root / "notebooks").glob("**/*.ipynb")):
        rel = nb.relative_to(root)
        if ".ipynb_checkpoints" in nb.parts:
            continue
        if not NOTEBOOK_NAME.match(nb.name):
            errors.append(f"{rel}: nome fora do padrão NN-iniciais-descricao.ipynb")
        cells = json.loads(nb.read_text()).get("cells", [])
        if any(c.get("outputs") or c.get("execution_count") for c in cells):
            errors.append(f"{rel}: notebook com outputs (rode o pre-commit / nbstripout)")
    return errors


def check_tests_per_module(root: Path) -> list[str]:
    pkg = find_package(root)
    if pkg is None:
        return []
    return [
        f"{mod.relative_to(root)} não tem teste correspondente em tests/test_{mod.stem}.py"
        for mod in sorted(pkg.glob("*.py"))
        if mod.stem not in MODULES_WITHOUT_TESTS
        and not (root / "tests" / f"test_{mod.stem}.py").is_file()
    ]


def check_no_absolute_paths(root: Path) -> list[str]:
    errors = []
    for py in sorted((root / "src").glob("**/*.py")):
        for n, line in enumerate(py.read_text().splitlines(), start=1):
            if ABSOLUTE_PATH.search(line):
                errors.append(f"{py.relative_to(root)}:{n}: caminho absoluto — use paths.py")
    return errors


def _run_pipeline(root: Path, module: str, env: dict[str, str], *args: str) -> str | None:
    result = subprocess.run(
        ["uv", "run", "--no-sync", "python", "-m", module, *args],
        cwd=root,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return f"`python -m {module}` falhou:\n{result.stderr.strip()[-2000:]}"
    return None


def check_pipeline_contract(root: Path) -> list[str]:
    """Treina 2x e faz inferência sobre a amostra em tests/fixtures; valida artefatos e seed."""
    pkg = find_package(root)
    fixture = root / SAMPLE_FIXTURE
    if pkg is None:
        return []
    if not fixture.is_file():
        return [f"amostra ausente: {SAMPLE_FIXTURE} (dados pequenos para testar o pipeline)"]

    metrics = []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            env = {
                "RAW_FILE": str(fixture),
                "DATA_DIR": str(out / "data"),
                "MODELS_DIR": str(out / "models"),
                "REPORTS_DIR": str(out / "reports"),
            }
            if err := _run_pipeline(root, f"{pkg.name}.pipelines.train", env):
                return [err]
            model, metrics_file = out / "models/model.joblib", out / "reports/metrics.json"
            missing = [str(p.relative_to(out)) for p in (model, metrics_file) if not p.is_file()]
            if missing:
                return [f"treino não gerou: {', '.join(missing)}"]
            metrics.append(json.loads(metrics_file.read_text()))

            if err := _run_pipeline(root, f"{pkg.name}.pipelines.predict", env, str(fixture)):
                return [err]
            if not (out / "data/predictions/predictions.csv").is_file():
                return ["inferência não gerou data/predictions/predictions.csv"]

    if metrics[0] != metrics[1]:
        return [f"treino não é reprodutível com a mesma seed: {metrics[0]} != {metrics[1]}"]
    return []


CHECKS: dict[str, Callable[[Path], list[str]]] = {
    "estrutura de pastas": check_structure,
    "sem dados/modelos no git": check_no_committed_data,
    "notebooks": check_notebooks,
    "teste para cada módulo": check_tests_per_module,
    "sem caminhos absolutos": check_no_absolute_paths,
    "contrato do pipeline (treino + inferência + seed)": check_pipeline_contract,
}
