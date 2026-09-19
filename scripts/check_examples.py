#!/usr/bin/env python3
"""Run every command the documentation claims you can run, and check its output.

Documentation rots quietly. A command that stopped working, or an output block
pasted three refactors ago, looks exactly like one that still holds — until a
reader tries it. This turns both into a test.

Two checks, and the second is the one that catches drift:

1. **Commands run.** Every line inside a ```bash fence, anywhere in the repo's
   markdown, is executed and must exit zero.

2. **Shown output is real.** An unlabelled ``` block immediately after a bash
   block is a claim about what that command prints. Every non-elided line of it
   must actually appear in the output.

Usage:
    python3 scripts/check_examples.py            # everything
    python3 scripts/check_examples.py chess      # just files matching "chess"
    python3 scripts/check_examples.py --verbose  # show each command as it runs
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TIMEOUT_SECONDS = 180

#: Commands we deliberately do not execute, and why. Anything not matched here
#: runs for real -- the list is meant to stay short.
SKIPPED = {
    "git clone": "would hit the network and clone into the working tree",
    "cd lld-python": "only meaningful right after the clone above",
    "pip install": "would modify the environment",
    "ruff format .": "rewrites files; CI checks formatting separately",
    "scripts/new_problem.py": "would scaffold a real directory into problems/",
    # The docs tell you to run this script, so without this it runs itself,
    # which runs itself, until the timeout kills the outermost one.
    "scripts/check_examples.py": "that is this script; running it would recurse",
}

#: Marks an elided line inside a shown output block. A line that is only this
#: is skipped rather than searched for.
ELISION = {"...", "...[snip]...", "…"}

#: Parts of an output line that legitimately change between runs. Both the
#: claimed and the actual line are masked through these before comparing, so a
#: timestamp or a temporary path does not have to be exempted wholesale -- the
#: rest of the line is still checked.
VARIABLE_PARTS = [
    (re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"), "<timestamp>"),
    (re.compile(r"\b\d{9,10}\.\d+\b"), "<epoch>"),
    (re.compile(r"(/var/folders/|/tmp/)\S+"), "<tmpdir>"),
    (re.compile(r"\buser\d+\b"), "<user>"),
]


def normalise(line: str) -> str:
    """Mask the parts of a line that change run to run."""
    for pattern, placeholder in VARIABLE_PARTS:
        line = pattern.sub(placeholder, line)
    return line


@dataclass
class Example:
    """One documented command, with whatever output the docs claim for it."""

    source: Path
    line_number: int
    command: str
    expected_output: list[str] = field(default_factory=list)

    @property
    def location(self) -> str:
        return f"{self.source.relative_to(REPO_ROOT)}:{self.line_number}"

    def skip_reason(self) -> str | None:
        for prefix, reason in SKIPPED.items():
            if prefix in self.command:
                return reason
        return None


def parse_markdown(path: Path) -> list[Example]:
    """Pull bash commands, and any output block that follows them, out of one file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    examples: list[Example] = []

    index = 0
    while index < len(lines):
        if lines[index].strip() != "```bash":
            index += 1
            continue

        # Collect the commands in this fence.
        index += 1
        commands: list[tuple[int, str]] = []
        while index < len(lines) and lines[index].strip() != "```":
            text = lines[index].strip()
            if text and not text.startswith("#"):
                commands.append((index + 1, text))
            index += 1
        index += 1  # past the closing fence

        # An unlabelled fence within a couple of lines is a claim about output.
        expected: list[str] = []
        lookahead = index
        while lookahead < len(lines) and not lines[lookahead].strip():
            lookahead += 1
        if lookahead < len(lines) and lines[lookahead].strip() == "```":
            lookahead += 1
            while lookahead < len(lines) and lines[lookahead].strip() != "```":
                expected.append(lines[lookahead])
                lookahead += 1

        for position, (line_number, command) in enumerate(commands):
            # Output belongs to the last command in the block.
            is_last = position == len(commands) - 1
            examples.append(Example(path, line_number, command, expected if is_last else []))

    return examples


def run(example: Example) -> tuple[bool, str, str]:
    """Execute one command. Returns (ok, output, detail)."""
    try:
        completed = subprocess.run(
            ["bash", "-c", example.command],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return False, "", f"timed out after {TIMEOUT_SECONDS}s"

    output = completed.stdout + completed.stderr
    if completed.returncode != 0:
        tail = "\n".join(output.strip().splitlines()[-6:])
        return False, output, f"exited {completed.returncode}\n{_indent(tail)}"

    return True, output, ""


def check_output(example: Example, actual: str) -> list[str]:
    """Every non-elided claimed line must really appear in the output."""
    actual_lines = {normalise(line.rstrip()) for line in actual.splitlines()}
    missing = []

    for claimed in example.expected_output:
        text = claimed.rstrip()
        if not text.strip() or text.strip() in ELISION:
            continue

        masked = normalise(text)

        # A trailing "..." inside a line means the rest was trimmed when pasting,
        # so only the part before it has to match.
        if masked.strip().endswith("...") and not masked.strip().startswith("..."):
            prefix = masked.rsplit("...", 1)[0].rstrip()
            if any(line.startswith(prefix) for line in actual_lines):
                continue
        elif masked in actual_lines:
            continue

        missing.append(text)

    return missing


def _indent(text: str, prefix: str = "        ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())


def collect(only: list[str]) -> list[Example]:
    examples = []
    for path in sorted(REPO_ROOT.glob("**/*.md")):
        if any(part in {".git", "node_modules", ".venv"} for part in path.parts):
            continue
        if only and not any(term in str(path) for term in only):
            continue
        examples.extend(parse_markdown(path))
    return examples


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run and verify every documented example.")
    parser.add_argument("only", nargs="*", help="Only check files matching these terms.")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    examples = collect(args.only)
    if not examples:
        print("No examples found.", file=sys.stderr)
        return 1

    ran = skipped = failed = drifted = 0
    current_file = None

    for example in examples:
        if example.source != current_file:
            current_file = example.source
            print(f"\n{example.source.relative_to(REPO_ROOT)}")

        reason = example.skip_reason()
        if reason:
            skipped += 1
            if args.verbose:
                print(f"  skip  {example.command}\n        ({reason})")
            continue

        ok, output, detail = run(example)
        ran += 1

        if not ok:
            failed += 1
            print(f"  FAIL  {example.command}")
            print(_indent(detail))
            continue

        missing = check_output(example, output)
        if missing:
            drifted += 1
            print(f"  DRIFT {example.command}")
            print(f"        the docs show {len(missing)} line(s) the command does not print:")
            for line in missing[:6]:
                print(f"          {line!r}")
            if len(missing) > 6:
                print(f"          ... and {len(missing) - 6} more")
            continue

        shown = len(example.expected_output)
        claim = f" (+{shown} output lines)" if shown else ""
        print(f"  ok    {example.command}{claim}")

    print(
        f"\n{ran} command(s) run, {skipped} skipped, {failed} failed, {drifted} with stale output."
    )

    if failed or drifted:
        print(
            "\nA FAIL means the documented command does not work.\n"
            "A DRIFT means it works but the README shows output it no longer produces.",
            file=sys.stderr,
        )
        return 1

    print("Every documented example runs, and every shown output is real.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
