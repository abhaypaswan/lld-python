"""Runnable demo for the text editor.

python3 src/main.py
python3 src/main.py --interactive
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from text_editor import Editor  # noqa: E402
from text_editor.history import NothingToRedo, NothingToUndo  # noqa: E402


def show(editor: Editor, note: str = "") -> None:
    caret = f"{editor.content[: editor.cursor]}|{editor.content[editor.cursor :]}"
    stack = f"undo:{editor.history.depth}"
    redo = " redo:1+" if editor.can_redo else ""
    print(f"  {caret!r:<42} [{stack}{redo}]" + (f"  {note}" if note else ""))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the text editor demo.")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args(argv)

    editor = Editor()

    if args.interactive:
        print("type <text> | undo | redo | select <a> <b> | cut | copy | paste |")
        print("replace <old> <new> | show | exit\n")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if line in {"exit", "quit"}:
                return 0
            if not line:
                continue

            action, *rest = line.split()
            try:
                if action == "type":
                    editor.type(" ".join(rest))
                elif action == "undo":
                    editor.undo()
                elif action == "redo":
                    editor.redo()
                elif action == "select":
                    editor.select(int(rest[0]), int(rest[1]))
                elif action == "cut":
                    editor.cut()
                elif action == "copy":
                    editor.copy()
                elif action == "paste":
                    editor.paste()
                elif action == "replace":
                    editor.replace_all(rest[0], rest[1])
                elif action != "show":
                    print(f"  unknown command: {action}")
            except (NothingToUndo, NothingToRedo, IndexError, ValueError) as exc:
                print(f"  {exc}")
            show(editor)
        return 0

    print("1. Typing character by character coalesces into ONE undo step.\n")
    for character in "hello":
        editor.type(character)
    show(editor, "five keystrokes")
    editor.undo()
    show(editor, "one undo took all five")
    editor.redo()
    show(editor, "and one redo brought them back")

    print("\n2. A newline ends the run, so undo stops at a natural boundary.\n")
    editor.type("\n")
    editor.type("world")
    show(editor)
    editor.undo()
    show(editor, "'world' only")

    print("\n3. The rule everyone gets wrong: a new edit clears the redo stack.\n")
    show(editor, f"can_redo={editor.can_redo}")
    editor.type("there")
    show(editor, f"typed something -> can_redo={editor.can_redo}")

    print("\n4. Replace-all is one undo step, not one per match.\n")
    editor = Editor("the cat sat on the mat")
    show(editor)
    editor.replace_all("at", "OG")
    show(editor, editor.history.undo_label)
    editor.undo()
    show(editor, "all three reversed together")

    print("\n5. Selection, clipboard, and undo over the top of them.\n")
    editor.select(4, 7)
    print(f"  selected {editor.document.selected_text!r}")
    editor.cut()
    show(editor, "cut")
    editor.move_cursor(len(editor))
    editor.paste()
    show(editor, "pasted at the end")
    editor.undo()
    editor.undo()
    show(editor, "both undone")

    print("\n6. Checkpoints are mementos: exact, and they reset the history.\n")
    editor.checkpoint("clean")
    editor.replace_all("the", "THE")
    show(editor, "edited")
    editor.restore("clean")
    show(editor, f"restored -> can_undo={editor.can_undo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
