#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

python3 - <<EOF
from pathlib import Path
import sys
import tomllib

PYPROJECT_PATH = Path("${REPO_ROOT}") / "pyproject.toml"
FORBIDDEN_RUNTIME_PACKAGES = frozenset({"sentence-transformers", "torch"})


def runtime_package_names() -> set[str]:
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


forbidden_present = FORBIDDEN_RUNTIME_PACKAGES & runtime_package_names()
if forbidden_present:
    print(
        "ERROR: Forbidden runtime dependencies found: "
        f"{sorted(forbidden_present)}",
        file=sys.stderr,
    )
    sys.exit(1)

print("OK: No torch or sentence-transformers in runtime dependencies")
EOF
