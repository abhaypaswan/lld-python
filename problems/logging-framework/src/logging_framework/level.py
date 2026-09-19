"""Severity levels, ordered so they can be compared."""

from __future__ import annotations

from enum import IntEnum


class LogLevel(IntEnum):
    """An IntEnum specifically so `record.level >= handler.level` works.

    Ordering is the entire job of a log level. A plain Enum would force every
    comparison through a lookup table, and a bare string would allow "DEBUG"
    to sort above "ERROR".
    """

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    FATAL = 50

    @classmethod
    def parse(cls, value: str | int | LogLevel) -> LogLevel:
        if isinstance(value, LogLevel):
            return value
        if isinstance(value, int):
            return cls(value)

        name = str(value).strip().upper()
        if name in cls.__members__:
            return cls[name]

        known = ", ".join(level.name.lower() for level in cls)
        raise ValueError(f"{value!r} is not a log level. Try one of: {known}")

    def __str__(self) -> str:
        return self.name
