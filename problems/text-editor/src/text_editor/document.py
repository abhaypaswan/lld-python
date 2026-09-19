"""The document, and the Memento that captures its whole state.

`Document` is the originator: it owns the text and the cursor, and it is the
only thing that can produce or restore a `DocumentState`. The state object
itself is opaque -- frozen, with no methods that let anyone poke at the
document through it.

That opacity is the part of Memento people skip. A snapshot that hands out a
mutable reference to the document's internals is not a snapshot; it is a second
way to corrupt the thing you were trying to protect.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentState:
    """A memento: everything needed to put the document back as it was.

    Frozen, so a snapshot taken now still describes *now* when it is restored
    later. A mutable snapshot of a mutable document is worth nothing.
    """

    content: str
    cursor: int
    selection: tuple[int, int] | None = None

    @property
    def length(self) -> int:
        return len(self.content)


class Document:
    """The originator: holds the text, and knows how to snapshot itself."""

    def __init__(self, content: str = ""):
        self._content = content
        self._cursor = len(content)
        self._selection: tuple[int, int] | None = None

    # -- reading ----------------------------------------------------------

    @property
    def content(self) -> str:
        return self._content

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def selection(self) -> tuple[int, int] | None:
        return self._selection

    @property
    def selected_text(self) -> str:
        if self._selection is None:
            return ""
        start, end = self._selection
        return self._content[start:end]

    def __len__(self) -> int:
        return len(self._content)

    def text_between(self, start: int, end: int) -> str:
        return self._content[start:end]

    # -- the memento ------------------------------------------------------

    def snapshot(self) -> DocumentState:
        return DocumentState(self._content, self._cursor, self._selection)

    def restore(self, state: DocumentState) -> None:
        self._content = state.content
        self._cursor = state.cursor
        self._selection = state.selection

    # -- writing ----------------------------------------------------------

    def insert(self, position: int, text: str) -> None:
        position = self._clamp(position)
        self._content = self._content[:position] + text + self._content[position:]
        self._cursor = position + len(text)
        self._selection = None

    def delete(self, start: int, end: int) -> str:
        """Remove [start, end) and return what was removed."""
        start, end = self._normalise(start, end)
        removed = self._content[start:end]
        self._content = self._content[:start] + self._content[end:]
        self._cursor = start
        self._selection = None
        return removed

    def replace(self, start: int, end: int, text: str) -> str:
        start, end = self._normalise(start, end)
        removed = self._content[start:end]
        self._content = self._content[:start] + text + self._content[end:]
        self._cursor = start + len(text)
        self._selection = None
        return removed

    # -- cursor and selection ---------------------------------------------

    def move_cursor(self, position: int) -> int:
        """Move the caret, dropping any selection.

        Clicking elsewhere deselects, in every editor ever written. Leaving the
        selection alive means the next thing typed replaces text nowhere near
        where the user is now looking.
        """
        self._cursor = self._clamp(position)
        self._selection = None
        return self._cursor

    def select(self, start: int, end: int) -> tuple[int, int]:
        self._selection = self._normalise(start, end)
        self._cursor = self._selection[1]
        return self._selection

    def clear_selection(self) -> None:
        self._selection = None

    # -- bounds -----------------------------------------------------------

    def _clamp(self, position: int) -> int:
        """Positions are clamped, not rejected.

        A cursor pushed past the end by a repeated key is normal editor
        behaviour, not an error. Raising here would mean every caller guarding
        every arrow key.
        """
        return max(0, min(position, len(self._content)))

    def _normalise(self, start: int, end: int) -> tuple[int, int]:
        """Clamp a range and put it the right way round.

        Selecting backwards -- dragging right to left -- gives start > end, and
        every caller downstream would otherwise have to remember that.
        """
        start, end = self._clamp(start), self._clamp(end)
        return (end, start) if start > end else (start, end)

    def __str__(self) -> str:
        return self._content
