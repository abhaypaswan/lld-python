"""Command: every edit knows how to do itself and how to undo itself.

Two ways to build undo, and the choice is a memory trade:

**Memento** -- snapshot the whole document before each edit, restore on undo.
Simple and always correct, but every keystroke in a 10 MB file costs 10 MB.

**Command** -- store only what is needed to invert this one edit. Typing one
character remembers one character. Undo cost is proportional to the *edit*, not
to the document.

Commands are the primary mechanism here, which is what real editors do. Memento
is still used, for the two places where it earns its keep: cursor and selection,
which are small and genuinely awkward to invert, and periodic checkpoints.

That mixture is the answer to this problem. "Command, with a memento for the
bits that are cheap to snapshot and painful to reverse" beats either alone.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .document import Document, DocumentState


class EditorCommand(ABC):
    """One reversible edit."""

    #: Human-readable, for an Edit menu that says "Undo Typing".
    label: str = "Edit"

    def __init__(self):
        #: Cursor and selection before the edit. Small, and much simpler to
        #: restore wholesale than to recompute from the inverse operation.
        self._before: DocumentState | None = None
        self.executed = False

    def execute(self, document: Document) -> None:
        self._before = document.snapshot()
        self.do(document)
        self.executed = True

    def undo(self, document: Document) -> None:
        if not self.executed:
            raise RuntimeError(f"{self.label} was never executed, so it cannot be undone")

        self.revert(document)
        if self._before is not None:
            # Content is restored by `revert`; this puts the caret back where
            # the user actually left it.
            document.move_cursor(self._before.cursor)
            if self._before.selection is not None:
                document.select(*self._before.selection)
            else:
                document.clear_selection()

    @abstractmethod
    def do(self, document: Document) -> None:
        """Apply the edit."""

    @abstractmethod
    def revert(self, document: Document) -> None:
        """Undo the content change. The inverse of `do`."""

    def merge_with(self, other: EditorCommand) -> EditorCommand | None:
        """Combine two commands into one undo step, or return None.

        Real editors do not make you press undo once per character. Typing
        "hello" is one undo, and this is where that happens.
        """
        return None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.label!r})"


class InsertCommand(EditorCommand):
    """Insert text. Inverted by deleting exactly what was inserted."""

    label = "Typing"

    def __init__(self, position: int, text: str, coalescable: bool = False):
        super().__init__()
        self.position = position
        self.text = text
        #: Only keystrokes coalesce. A programmatic insert() is one deliberate
        #: edit and should stay one undo step, even if it happens to land right
        #: where the previous one ended -- adjacency is not intent.
        self.coalescable = coalescable

    def do(self, document: Document) -> None:
        document.insert(self.position, self.text)

    def revert(self, document: Document) -> None:
        document.delete(self.position, self.position + len(self.text))

    def merge_with(self, other: EditorCommand) -> EditorCommand | None:
        """Coalesce consecutive typing into one undo step.

        Only when `other` continues directly where this one ended, and only
        while neither contains a newline -- a line break is a natural place for
        a user to expect undo to stop.
        """
        if not isinstance(other, InsertCommand):
            return None
        if not (self.coalescable and other.coalescable):
            return None
        if other.position != self.position + len(self.text):
            return None
        if "\n" in self.text or "\n" in other.text:
            return None
        if len(self.text) + len(other.text) > 80:
            return None

        merged = InsertCommand(self.position, self.text + other.text, coalescable=True)
        merged._before = self._before
        merged.executed = True
        return merged


class DeleteCommand(EditorCommand):
    """Delete a range. Inverted by re-inserting what was removed.

    The removed text is captured at execute time, not at construction, because
    at construction the document may not yet be in the state this command
    expects -- a redo of a whole stack replays commands in order.
    """

    label = "Delete"

    def __init__(self, start: int, end: int):
        super().__init__()
        self.start = start
        self.end = end
        self.removed = ""

    def do(self, document: Document) -> None:
        self.removed = document.delete(self.start, self.end)

    def revert(self, document: Document) -> None:
        document.insert(self.start, self.removed)


class ReplaceCommand(EditorCommand):
    """Swap a range for new text. Inverted by swapping it back."""

    label = "Replace"

    def __init__(self, start: int, end: int, text: str):
        super().__init__()
        self.start = start
        self.end = end
        self.text = text
        self.removed = ""

    def do(self, document: Document) -> None:
        self.removed = document.replace(self.start, self.end, self.text)

    def revert(self, document: Document) -> None:
        document.replace(self.start, self.start + len(self.text), self.removed)


class CompositeCommand(EditorCommand):
    """Several edits that undo as one step.

    Find-and-replace-all is the obvious case: twelve replacements the user
    thinks of as one action, and expects one undo to reverse.

    Undo runs in reverse order, which is not optional -- each edit shifts the
    positions the later ones were computed against.
    """

    def __init__(self, commands: list[EditorCommand], label: str = "Multiple edits"):
        super().__init__()
        self.commands = list(commands)
        self.label = label

    def do(self, document: Document) -> None:
        for command in self.commands:
            command.execute(document)

    def revert(self, document: Document) -> None:
        for command in reversed(self.commands):
            command.undo(document)
