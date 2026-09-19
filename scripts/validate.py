#!/usr/bin/env python3
"""Check that every problem in problems/ is complete and internally consistent.

Two layers of checking happen here:

1. JSON Schema validation of each meta.json against schema/problem.schema.json.
   This needs the `jsonschema` package. If it is missing we skip this layer and
   say so rather than failing, because layer 2 is the one that catches real rot.

2. Structural checks that no schema can express: does the entrypoint file
   actually exist, does the tests directory have tests in it, does the slug
   match the folder name, does the README carry a diagram when meta.json claims
   one. These run on the standard library alone.

Usage:
    python3 scripts/validate.py            # check everything
    python3 scripts/validate.py elevator-system parking-lot   # check a subset
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBLEMS_DIR = REPO_ROOT / "problems"
SCHEMA_PATH = REPO_ROOT / "schema" / "problem.schema.json"


class Problem:
    """One problems/<slug>/ directory, loaded and ready to be checked."""

    def __init__(self, directory: Path):
        self.dir = directory
        self.slug = directory.name
        self.meta_path = directory / "meta.json"
        self.readme_path = directory / "README.md"
        self.meta: dict | None = None
        self.load_error: str | None = None

        try:
            self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.load_error = "meta.json is missing"
        except json.JSONDecodeError as exc:
            self.load_error = f"meta.json is not valid JSON: {exc}"


def discover(only: list[str] | None = None) -> list[Problem]:
    """Return every problem directory, or just the ones named in `only`."""
    if not PROBLEMS_DIR.is_dir():
        return []

    directories = sorted(d for d in PROBLEMS_DIR.iterdir() if d.is_dir())
    if only:
        wanted = set(only)
        directories = [d for d in directories if d.name in wanted]

        missing = wanted - {d.name for d in directories}
        for slug in sorted(missing):
            print(f"  ! no such problem: {slug}", file=sys.stderr)

    return [Problem(d) for d in directories]


def schema_errors(problem: Problem, validator) -> list[str]:
    """Run the meta.json through JSON Schema, if a validator was built."""
    if validator is None or problem.meta is None:
        return []

    errors = []
    for error in validator.iter_errors(problem.meta):
        location = ".".join(str(part) for part in error.absolute_path) or "(root)"
        errors.append(f"{location}: {error.message}")
    return sorted(errors)


def structural_errors(problem: Problem) -> list[str]:
    """Checks that depend on files on disk, not just the shape of the JSON."""
    if problem.meta is None:
        return []

    meta = problem.meta
    errors = []

    declared_slug = meta.get("slug")
    if declared_slug and declared_slug != problem.slug:
        errors.append(
            f"slug is {declared_slug!r} but the directory is named {problem.slug!r}"
        )

    if not problem.readme_path.is_file():
        errors.append("README.md is missing")

    entrypoint = meta.get("entrypoint")
    if entrypoint and not (problem.dir / entrypoint).is_file():
        errors.append(f"entrypoint {entrypoint} does not exist")

    tests = meta.get("tests")
    if tests:
        tests_dir = problem.dir / tests
        if not tests_dir.is_dir():
            errors.append(f"tests directory {tests} does not exist")
        elif not list(tests_dir.glob("test_*.py")):
            errors.append(f"{tests} contains no test_*.py files")

    diagram = meta.get("diagram") or {}
    if diagram.get("mermaid"):
        readme = _read_text(problem.readme_path)
        if "```mermaid" in readme:
            # A fenced block that never closes silently swallows the rest of the
            # README on GitHub, so count the fences rather than just finding one.
            if readme.count("```") % 2 != 0:
                errors.append("README.md has an unclosed code fence")
        else:
            errors.append("diagram.mermaid is true but README.md has no ```mermaid block")

    for key in ("light", "dark", "svg"):
        relative = diagram.get(key)
        if relative and not (problem.dir / relative).is_file():
            errors.append(f"diagram.{key} points at {relative}, which does not exist")

    return errors


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def build_validator():
    """Build a JSON Schema validator, or return None if jsonschema is absent."""
    try:
        import jsonschema
    except ImportError:
        print(
            "  note: jsonschema is not installed, so schema checks are being skipped.\n"
            "        Install it with: pip install -r requirements-dev.txt",
            file=sys.stderr,
        )
        return None

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return jsonschema.Draft7Validator(schema)


def main(argv: list[str]) -> int:
    problems = discover(argv or None)
    if not problems:
        print("No problems found under problems/.", file=sys.stderr)
        return 1

    validator = build_validator()
    failed = 0

    for problem in problems:
        if problem.load_error:
            print(f"FAIL {problem.slug}\n       {problem.load_error}")
            failed += 1
            continue

        errors = schema_errors(problem, validator) + structural_errors(problem)
        if errors:
            failed += 1
            print(f"FAIL {problem.slug}")
            for error in errors:
                print(f"       {error}")
        else:
            print(f"ok   {problem.slug}")

    print()
    if failed:
        print(f"{failed} of {len(problems)} problems have problems.")
        return 1

    print(f"All {len(problems)} problems look good.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
