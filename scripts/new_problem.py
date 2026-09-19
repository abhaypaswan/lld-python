#!/usr/bin/env python3
"""Scaffold a new problem directory.

Creates everything `scripts/validate.py` expects, filled in with placeholders
and TODOs, so a contributor starts from something that already runs and already
passes validation rather than from an empty folder and a list of rules.

    python3 scripts/new_problem.py rate-limiter
    python3 scripts/new_problem.py chess --title "Design Chess" --difficulty hard

The generated problem is deliberately trivial but complete: the demo runs, the
test passes, and `validate.py` is happy. Replace the pieces one at a time.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBLEMS_DIR = REPO_ROOT / "problems"

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def title_from(slug: str) -> str:
    return "Design " + " ".join(word.capitalize() for word in slug.split("-"))


def package_from(slug: str) -> str:
    """The slug with underscores.

    Must be unique across the repo: every problem's src/ goes on sys.path at
    once, so two problems sharing a package name would shadow each other.
    """
    return slug.replace("-", "_")


def render_init(package: str, title: str) -> str:
    return f'''"""{title}. TODO: one line on what this models."""

from .core import Example

__all__ = ["Example"]
'''


def render_core(package: str) -> str:
    return '''"""TODO: the real implementation goes here.

Some things the existing problems do that are worth copying:

- Inject clocks and random sources rather than calling time.time() or
  random.random() inside. No test should have to sleep.
- Return values instead of printing. The demo prints; the domain returns.
- Validate invariants at construction, so an impossible object cannot exist.
- Name the design decision in a comment where it is not obvious, and say what
  goes wrong without it.
"""

from __future__ import annotations


class Example:
    """TODO: replace this with the real thing."""

    def __init__(self, name: str):
        if not name.strip():
            raise ValueError("A name cannot be empty")
        self.name = name

    def describe(self) -> str:
        return f"Example({self.name})"
'''


def render_main(package: str, title: str) -> str:
    return f'''"""Runnable demo for {title.lower()}.

    python3 src/main.py

Must run to completion with no input: CI runs every problem's demo. Put any
interactive mode behind --interactive.

Make it show something worth seeing. The best demos here make a design decision
visible -- the rate limiter runs all four algorithms over the same traffic, the
cache replays one access pattern under three eviction policies.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from {package} import Example  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Run the {title.lower()} demo.").parse_args(argv)

    # TODO: replace with a demo that shows the design doing something.
    print(Example("placeholder").describe())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def render_test(package: str, slug: str) -> str:
    return f'''"""TODO: tests for {slug}.

Not for coverage. Pin down the behaviour the design exists to guarantee, and
the cases that are easy to get wrong:

- the failure that must leave nothing changed behind
- the arithmetic that has to come out exact
- the rule everyone forgets

If a published oracle exists for this domain, test against it.
"""

import pytest
from {package} import Example


def test_an_example_has_a_name():
    assert Example("first").describe() == "Example(first)"


def test_a_name_cannot_be_empty():
    with pytest.raises(ValueError, match="cannot be empty"):
        Example("   ")
'''


def render_meta(slug: str, title: str, difficulty: str, minutes: int) -> str:
    meta = {
        "slug": slug,
        "title": title,
        "difficulty": difficulty,
        "summary": (
            f"TODO: one or two sentences describing {title.lower()}. This is the card "
            f"blurb on goatengineer.com, so it has to stand alone without the statement."
        ),
        "tags": ["todo"],
        "patterns": ["strategy"],
        "concepts": ["TODO: what this problem teaches beyond the patterns"],
        "entrypoint": "src/main.py",
        "tests": "tests",
        "estimatedMinutes": minutes,
        "askedAt": [],
        "diagram": {"mermaid": True},
        "extensions": ["TODO: a follow-up an interviewer would ask"],
    }
    return json.dumps(meta, indent=2, ensure_ascii=False) + "\n"


def render_readme(slug: str, title: str, difficulty: str, minutes: int) -> str:
    badge = {"easy": "🟢 Easy", "medium": "🟡 Medium", "hard": "🔴 Hard"}[difficulty]

    return f"""# {title}

> **Difficulty:** {badge} · **Time:** ~{minutes} min · **Patterns:** TODO

TODO: one paragraph on what makes this problem interesting. Not what it is —
what separates a good answer from one that merely works.

## The problem

TODO: what the candidate is asked to build.

## Requirements

1. TODO
2. TODO

## Assumptions

- TODO: what is deliberately out of scope, and why.

## Class diagram

```mermaid
classDiagram
    class Example {{
        +str name
        +describe() str
    }}
```

## How the design works

TODO: this is the section that matters. For each pattern used, say **why** —
what changes independently of what, and what breaks if they are folded together.

"This uses Strategy" is not interesting. "This uses Strategy because the
eviction rule and the cache change for different reasons, and here is the bug
that avoids" is.

Worth covering if they apply:

- a decision that looks reasonable and is wrong, and how it fails
- an ordering that has to be a particular way round
- an invariant the tests pin down

## Running it

```bash
cd problems/{slug} && python3 src/main.py
```

```
TODO: paste real output here.
```

## Tests

```bash
python3 -m pytest problems/{slug} -v
```

## Follow-ups an interviewer will ask

- **TODO:** and what it does to the design.
"""


def create(slug: str, title: str, difficulty: str, minutes: int, force: bool) -> Path:
    directory = PROBLEMS_DIR / slug
    package = package_from(slug)

    if directory.exists() and not force:
        raise SystemExit(
            f"{directory.relative_to(REPO_ROOT)} already exists. Pass --force to overwrite it."
        )

    files = {
        directory / "README.md": render_readme(slug, title, difficulty, minutes),
        directory / "meta.json": render_meta(slug, title, difficulty, minutes),
        directory / "src" / "main.py": render_main(package, title),
        directory / "src" / package / "__init__.py": render_init(package, title),
        directory / "src" / package / "core.py": render_core(package),
        directory / "tests" / f"test_{package}.py": render_test(package, slug),
    }

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scaffold a new LLD problem.")
    parser.add_argument("slug", help="Directory name, kebab-case, e.g. rate-limiter")
    parser.add_argument("--title", help='Defaults to "Design <Slug Words>".')
    parser.add_argument("--difficulty", default="medium", choices=["easy", "medium", "hard"])
    parser.add_argument("--minutes", type=int, default=60, help="Estimated time.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing one.")
    args = parser.parse_args(argv)

    if not SLUG_PATTERN.match(args.slug):
        print(
            f"{args.slug!r} is not a valid slug. Use lowercase words joined by "
            f"hyphens, e.g. movie-ticket-booking.",
            file=sys.stderr,
        )
        return 1

    title = args.title or title_from(args.slug)
    directory = create(args.slug, title, args.difficulty, args.minutes, args.force)
    relative = directory.relative_to(REPO_ROOT)

    print(f"Created {relative}/\n")
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            print(f"  {path.relative_to(REPO_ROOT)}")

    print(
        f"\nIt already runs and passes validation, so you can replace the pieces\n"
        f"one at a time and keep everything green:\n\n"
        f"  python3 -m pytest {relative}\n"
        f"  cd {relative} && python3 src/main.py\n"
        f"  python3 scripts/validate.py {args.slug}\n\n"
        f"When the meta.json is filled in, refresh the generated files:\n\n"
        f"  python3 scripts/build_catalog.py\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
