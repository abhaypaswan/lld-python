"""The editor: the façade a UI would talk to."""

from __future__ import annotations

from .commands import (
    CompositeCommand,
    DeleteCommand,
    EditorCommand,
    InsertCommand,
    ReplaceCommand,
)
from .document import Document, DocumentState
from .history import History


class Editor:
    """Document, history and clipboard, behind one set of verbs.

    Every mutation goes through `history.execute`, which is what guarantees
    everything is undoable. An edit that touched the document directly would be
    invisible to undo and would silently desynchronise the stack -- so there is
    deliberately no public path to the document's mutators from here.
    """

    def __init__(self, content: str = "", undo_limit: int | None = 200, coalesce: bool = True):
        self.document = Document(content)
        self.history = History(self.document, limit=undo_limit, coalesce=coalesce)
        self.clipboard: str = ""
        self._checkpoints: dict[str, DocumentState] = {}

    # -- reading ----------------------------------------------------------

    @property
    def content(self) -> str:
        return self.document.content

    @property
    def cursor(self) -> int:
        return self.document.cursor

    def __len__(self) -> int:
        return len(self.document)

    # -- editing ----------------------------------------------------------

    def type(self, text: str) -> EditorCommand:
        """Insert at the cursor, replacing the selection if there is one."""
        selection = self.document.selection
        if selection is not None:
            return self.history.execute(ReplaceCommand(*selection, text))

        return self.history.execute(InsertCommand(self.document.cursor, text, coalescable=True))

    def insert(self, position: int, text: str) -> EditorCommand:
        return self.history.execute(InsertCommand(position, text))

    def delete(self, start: int, end: int) -> EditorCommand:
        return self.history.execute(DeleteCommand(start, end))

    def backspace(self, count: int = 1) -> EditorCommand | None:
        selection = self.document.selection
        if selection is not None:
            return self.history.execute(DeleteCommand(*selection))

        cursor = self.document.cursor
        if cursor == 0:
            return None
        return self.history.execute(DeleteCommand(max(0, cursor - count), cursor))

    def replace(self, start: int, end: int, text: str) -> EditorCommand:
        return self.history.execute(ReplaceCommand(start, end, text))

    # -- selection and clipboard ------------------------------------------

    def move_cursor(self, position: int) -> int:
        return self.document.move_cursor(position)

    def select(self, start: int, end: int) -> tuple[int, int]:
        return self.document.select(start, end)

    def select_all(self) -> tuple[int, int]:
        return self.document.select(0, len(self.document))

    def copy(self) -> str:
        self.clipboard = self.document.selected_text
        return self.clipboard

    def cut(self) -> str:
        """Copy, then delete. Not undoable as two steps -- users expect one."""
        selection = self.document.selection
        if selection is None:
            return ""

        self.clipboard = self.document.selected_text
        self.history.execute(DeleteCommand(*selection))
        return self.clipboard

    def paste(self) -> EditorCommand | None:
        if not self.clipboard:
            return None
        return self.type(self.clipboard)

    # -- find and replace -------------------------------------------------

    def find(self, needle: str) -> list[int]:
        """Every start offset of `needle`, including overlapping matches."""
        if not needle:
            return []

        offsets, start = [], 0
        while (found := self.document.content.find(needle, start)) != -1:
            offsets.append(found)
            start = found + 1
        return offsets

    def replace_all(self, needle: str, replacement: str) -> EditorCommand | None:
        """One undo step for the whole operation, not one per match."""
        offsets = self.find(needle)
        if not offsets:
            return None

        # Right to left, so each replacement cannot shift the offsets of the
        # ones still to come.
        commands = [
            ReplaceCommand(offset, offset + len(needle), replacement)
            for offset in sorted(offsets, reverse=True)
        ]
        label = f"Replace {len(commands)} occurrence" + ("s" if len(commands) > 1 else "")
        return self.history.execute(CompositeCommand(commands, label))

    # -- undo and redo ----------------------------------------------------

    def undo(self) -> EditorCommand:
        return self.history.undo()

    def redo(self) -> EditorCommand:
        return self.history.redo()

    @property
    def can_undo(self) -> bool:
        return self.history.can_undo

    @property
    def can_redo(self) -> bool:
        return self.history.can_redo

    # -- checkpoints ------------------------------------------------------

    def checkpoint(self, name: str) -> DocumentState:
        """Save a named memento. Cheap for small documents, and exact."""
        state = self.document.snapshot()
        self._checkpoints[name] = state
        return state

    def restore(self, name: str) -> DocumentState:
        """Jump back to a checkpoint.

        This clears the history rather than trying to reconcile it: the stack
        describes a path the document is no longer on, and keeping it would let
        an undo apply an inverse to text it never saw.
        """
        state = self._checkpoints.get(name)
        if state is None:
            known = ", ".join(sorted(self._checkpoints)) or "(none)"
            raise KeyError(f"No checkpoint {name!r}. Saved checkpoints: {known}")

        self.document.restore(state)
        self.history.clear()
        return state

    @property
    def checkpoints(self) -> list[str]:
        return sorted(self._checkpoints)
