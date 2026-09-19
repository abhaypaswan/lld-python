"""Make every problem importable so `pytest` works from the repo root.

Each problem keeps its code in `problems/<slug>/src/<package_name>/`, where the
package name is the slug with dashes turned into underscores. Because those
package names are unique across the repo, we can put every `src` directory on
sys.path at once without two problems fighting over a shared module name like
`model` or `strategy`.

That is the whole reason for the extra package directory. Without it, the second
problem to define `model` would silently get the first one's module.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
PROBLEMS_DIR = REPO_ROOT / "problems"


def _register_source_roots() -> None:
    for problem_dir in sorted(PROBLEMS_DIR.iterdir()) if PROBLEMS_DIR.is_dir() else []:
        src = problem_dir / "src"
        if src.is_dir():
            sys.path.insert(0, str(src))


_register_source_roots()
