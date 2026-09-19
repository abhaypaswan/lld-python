"""Runnable demo for the in-memory file system.

python3 src/main.py
python3 src/main.py --interactive
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from file_system import FileSystem, NotADirectory, PathNotFound  # noqa: E402

ERRORS = (
    PathNotFound,
    NotADirectory,
    FileExistsError,
    FileNotFoundError,
    IsADirectoryError,
    ValueError,
)

PROJECT = {
    "/README.md": "# Demo project\n\nAn in-memory file system.\n",
    "/pyproject.toml": "[project]\nname = 'demo'\n",
    "/src/demo/__init__.py": "",
    "/src/demo/core.py": "def run():\n    return 42\n",
    "/src/demo/models.py": "class User:\n    pass\n",
    "/src/demo/utils/text.py": "def slug(s):\n    return s.lower()\n",
    "/tests/test_core.py": "def test_run():\n    assert True\n",
    "/tests/test_models.py": "def test_user():\n    assert True\n",
    "/docs/guide.md": "## Guide\n",
}


def build() -> FileSystem:
    fs = FileSystem()
    for path, content in PROJECT.items():
        fs.write(path, content)
    return fs


def interactive(fs: FileSystem) -> int:
    print("tree | ls <path> | cat <path> | du <path> | find <ext> |")
    print("mkdir <path> | write <path> <text> | rm <path> | mv <a> <b> | exit\n")

    while True:
        try:
            line = input("fs> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line in {"exit", "quit"}:
            return 0
        if not line:
            continue

        action, *args = line.split()
        try:
            if action == "tree":
                print(fs.tree(*args))
            elif action == "ls":
                print("  ".join(fs.ls(*args or ["/"])))
            elif action == "cat":
                print(fs.read(args[0]), end="")
            elif action == "du":
                print(fs.du(*args or ["/"]).summary())
            elif action == "find":
                print("\n".join(fs.find(extension=args[0])) or "(nothing)")
            elif action == "mkdir":
                fs.mkdir(args[0], parents=True)
            elif action == "write":
                fs.write(args[0], " ".join(args[1:]))
            elif action == "rm":
                fs.rm(args[0], recursive=True)
            elif action == "mv":
                fs.move(args[0], args[1])
            else:
                print(f"  unknown command: {action}")
        except ERRORS as exc:
            print(f"  {exc}")
        except IndexError:
            print("  that command needs more arguments")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the file system demo.")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args(argv)

    fs = build()
    if args.interactive:
        print(fs.tree() + "\n")
        return interactive(fs)

    print("A project tree. Sizes are computed, never stored.\n")
    print(fs.tree())

    usage = fs.du()
    print(f"\n{usage.summary()}")
    print(
        "  by extension: "
        + ", ".join(f"{ext} {size}b" for ext, size in sorted(usage.by_extension.items()))
    )

    print("\nSearching is a visitor, so it did not need a method on any node:")
    print(f"  *.py  -> {len(fs.find(extension='py'))} files")
    print(f"  *.md  -> {fs.find(extension='md')}")

    print("\nMoving a directory carries everything under it:")
    fs.mkdir("/lib")
    fs.move("/src/demo", "/lib/demo")
    print(f"  /lib/demo/utils/text.py exists: {fs.exists('/lib/demo/utils/text.py')}")
    print(f"  /src now holds: {fs.ls('/src') or '(nothing)'}")

    print("\nSize is recomputed from the tree, so it follows the move:")
    print(f"  /lib is {fs.size('/lib')} bytes, /src is {fs.size('/src')} bytes")

    print("\nAnd the errors are specific rather than generic:")
    for path in ("/nope.txt", "/README.md/inner"):
        try:
            fs.resolve(path)
        except ERRORS as exc:
            print(f"  {path:<20} {type(exc).__name__}: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
