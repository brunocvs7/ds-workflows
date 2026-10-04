import json
import subprocess

import pytest

from ds_conformance import checks


@pytest.fixture
def project(tmp_path):
    """Projeto mínimo conforme (sem rodar pipeline)."""
    for d in checks.REQUIRED_DIRS:
        (tmp_path / d).mkdir(parents=True)
        (tmp_path / d / ".gitkeep").touch()
    pkg = tmp_path / "src" / "meu_pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").touch()
    (pkg / "features.py").write_text("X = 1\n")
    (tmp_path / "tests" / "test_features.py").touch()
    for f in ("pyproject.toml", "uv.lock", ".pre-commit-config.yaml"):
        (tmp_path / f).touch()
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path


def _notebook(path, outputs):
    cell = {"cell_type": "code", "source": "1", "outputs": outputs, "execution_count": None}
    path.write_text(json.dumps({"cells": [cell]}))


def test_conforming_project_passes(project):
    for name, check in checks.CHECKS.items():
        if "pipeline" not in name:
            assert check(project) == [], name


def test_structure_missing_dir(project):
    (project / "models" / ".gitkeep").unlink()
    (project / "models").rmdir()
    assert checks.check_structure(project) == ["pasta obrigatória ausente: models/"]


def test_package_name_is_free(project):
    assert checks.find_package(project).name == "meu_pkg"


def test_committed_data_detected(project):
    (project / "data/raw/clientes.csv").write_text("a,b\n")
    subprocess.run(["git", "add", "-f", "data/raw/clientes.csv"], cwd=project, check=True)
    assert checks.check_no_committed_data(project) == [
        "arquivo de dados/modelo versionado no git: data/raw/clientes.csv"
    ]


def test_notebook_outputs(project):
    _notebook(project / "notebooks/Untitled.ipynb", outputs=[])
    assert checks.check_notebooks(project) == []

    _notebook(project / "notebooks/Untitled.ipynb", outputs=[{"text": "x"}])
    assert checks.check_notebooks(project) == [
        "notebooks/Untitled.ipynb: notebook com outputs (rode o pre-commit / nbstripout)"
    ]


def test_pipeline_requires_fixture(project):
    assert "amostra ausente" in checks.check_pipeline_contract(project)[0]
