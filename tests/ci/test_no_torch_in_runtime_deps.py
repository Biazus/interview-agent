from pathlib import Path

import tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

FORBIDDEN_RUNTIME_PACKAGES = frozenset({"sentence-transformers", "torch"})


def _runtime_package_names() -> set[str]:
    with PYPROJECT_PATH.open("rb") as handle:
        pyproject = tomllib.load(handle)

    dependencies = pyproject["project"]["dependencies"]
    return {
        dependency.split("[", maxsplit=1)[0]
        .split(">=", maxsplit=1)[0]
        .split("==", maxsplit=1)[0]
        .split("<=", maxsplit=1)[0]
        .strip()
        for dependency in dependencies
    }


def test_runtime_dependencies_exclude_torch_stack() -> None:
    runtime_packages = _runtime_package_names()
    forbidden_present = FORBIDDEN_RUNTIME_PACKAGES & runtime_packages

    assert not forbidden_present, (
        "PR1 removes torch stack from runtime deps; found: "
        f"{sorted(forbidden_present)}"
    )
