"""Chain of Responsibility: each handler decides, then passes the record on.

A record enters at the head of the chain and travels along it. Each handler
asks whether the record meets its own threshold; if so it writes it. Either
way, the record continues down the chain.

That "either way" is the design decision worth defending. The textbook Chain of
Responsibility stops at the first handler that handles the request -- correct
for an approval workflow, wrong for logging, where an ERROR should reach the
console *and* the file *and* the alerting sink. The chain here is about giving
every link a look, not about finding one owner.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from pathlib import Path

from .formatters import Formatter, SimpleFormatter, get_formatter
from .level import LogLevel
from .record import LogRecord


class Handler(ABC):
    """One link in the chain: a threshold, a formatter and a destination."""

    def __init__(
        self,
        level: LogLevel | str = LogLevel.DEBUG,
        formatter: Formatter | str | None = None,
    ):
        self.level = LogLevel.parse(level)
        self.formatter = (
            get_formatter(formatter)
            if isinstance(formatter, str)
            else (formatter or SimpleFormatter())
        )
        self._next: Handler | None = None

    def set_next(self, handler: Handler) -> Handler:
        """Append a handler and return it, so calls chain fluently."""
        self._next = handler
        return handler

    @property
    def next_handler(self) -> Handler | None:
        return self._next

    def handle(self, record: LogRecord) -> None:
        """Write the record if it clears our bar, then pass it on regardless."""
        if record.level >= self.level:
            self.emit(self.formatter.format(record), record)

        if self._next is not None:
            self._next.handle(record)

    @abstractmethod
    def emit(self, line: str, record: LogRecord) -> None:
        """Write one already-formatted line to wherever this handler points.

        The record comes along with the line so a handler can route on level
        without parsing the text back out of its own output.
        """

    def close(self) -> None:  # noqa: B027
        """Release anything held open. Safe to call more than once.

        Deliberately concrete and empty rather than abstract: most handlers
        hold nothing open, and forcing all of them to write `pass` would be
        noise. Only FileHandler overrides it.
        """


class ConsoleHandler(Handler):
    """Writes to stdout, or to stderr from WARNING up.

    Splitting the streams matters in practice: it is what lets an operator pipe
    normal output somewhere and still see problems on the terminal.
    """

    def __init__(
        self,
        level=LogLevel.DEBUG,
        formatter=None,
        stream=None,
        error_stream=None,
        split_at: LogLevel | str = LogLevel.WARNING,
    ):
        super().__init__(level, formatter)
        self.stream = stream if stream is not None else sys.stdout
        self.error_stream = error_stream if error_stream is not None else sys.stderr
        self.split_at = LogLevel.parse(split_at)

    def emit(self, line: str, record: LogRecord) -> None:
        target = self.error_stream if record.level >= self.split_at else self.stream
        print(line, file=target)


class FileHandler(Handler):
    """Appends to a file, opening it lazily.

    Lazily because a handler that opens its file in __init__ creates the file
    even for a run that never logs anything at its level.
    """

    def __init__(self, path, level=LogLevel.DEBUG, formatter=None):
        super().__init__(level, formatter)
        self.path = Path(path)
        self._file = None

    def emit(self, line: str, record: LogRecord) -> None:
        if self._file is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = self.path.open("a", encoding="utf-8")

        self._file.write(line + "\n")
        self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None


class MemoryHandler(Handler):
    """Keeps lines in a list. Used by the tests, and useful for a ring buffer."""

    def __init__(self, level=LogLevel.DEBUG, formatter=None, capacity: int | None = None):
        super().__init__(level, formatter)
        self.capacity = capacity
        self.lines: list[str] = []

    def emit(self, line: str, record: LogRecord) -> None:
        self.lines.append(line)
        if self.capacity is not None and len(self.lines) > self.capacity:
            del self.lines[0 : len(self.lines) - self.capacity]

    def clear(self) -> None:
        self.lines.clear()


def build_chain(*handlers: Handler) -> Handler | None:
    """Link handlers head to tail and return the head."""
    if not handlers:
        return None

    for current, following in zip(handlers, handlers[1:], strict=False):
        current.set_next(following)
    return handlers[0]
