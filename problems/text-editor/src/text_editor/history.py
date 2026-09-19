"""Two stacks, and the rule that catches everyone."""

from __future__ import annotations

from .commands import EditorCommand
from .document import Document


class NothingToUndo(Exception):
    """The undo stack is empty."""


class NothingToRedo(Exception):
    """The redo stack is empty."""


class History:
    """Undo and redo, as a pair of stacks.

    The rule people miss: **a new edit clears the redo stack.** Undo three
    times, then type something, and those three redos are gone -- the future
    you were about to redo into no longer exists, because the document took a
    different branch.

    Leaving them in place lets a redo replay an edit against text it was never
    computed against, which corrupts the document quietly rather than loudly.
    """

    def __init__(self, document: Document, limit: int | None = 200, coalesce: bool = True):
        self.document = document
        self.limit = limit
        self.coalesce = coalesce
        self._undo_stack: list[EditorCommand] = []
        self._redo_stack: list[EditorCommand] = []

    # -- state ------------------------------------------------------------

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def undo_label(self) -> str:
        return f"Undo {self._undo_stack[-1].label}" if self._undo_stack else "Undo"

    @property
    def redo_label(self) -> str:
        return f"Redo {self._redo_stack[-1].label}" if self._redo_stack else "Redo"

    @property
    def depth(self) -> int:
        return len(self._undo_stack)

    # -- running ----------------------------------------------------------

    def execute(self, command: EditorCommand) -> EditorCommand:
        command.execute(self.document)

        # The document has branched. Anything that was ahead of us is now
        # unreachable, and replaying it would apply an edit to text it was
        # never computed against.
        self._redo_stack.clear()

        if self.coalesce and self._undo_stack:
            merged = self._undo_stack[-1].merge_with(command)
            if merged is not None:
                self._undo_stack[-1] = merged
                return merged

        self._undo_stack.append(command)
        self._trim()
        return command

    def undo(self) -> EditorCommand:
        if not self._undo_stack:
            raise NothingToUndo("There is nothing to undo")

        command = self._undo_stack.pop()
        command.undo(self.document)
        self._redo_stack.append(command)
        return command

    def redo(self) -> EditorCommand:
        if not self._redo_stack:
            raise NothingToRedo("There is nothing to redo")

        command = self._redo_stack.pop()
        command.execute(self.document)
        self._undo_stack.append(command)
        return command

    def _trim(self) -> None:
        """Drop the oldest history past the limit.

        Unbounded undo is an unbounded memory leak in a long editing session.
        The oldest entries go, because nobody undoes four thousand steps.
        """
        if self.limit is not None and len(self._undo_stack) > self.limit:
            del self._undo_stack[: len(self._undo_stack) - self.limit]

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
