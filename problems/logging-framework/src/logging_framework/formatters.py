"""Strategy: how a record becomes text.

Separate from the handler because the two vary independently -- you may want
JSON on disk and plain text on the console, or the same format in both places.
Folding formatting into the handler forces a class per combination.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from .record import LogRecord


class Formatter(ABC):
    name: str = "formatter"

    @abstractmethod
    def format(self, record: LogRecord) -> str:
        """Render the record as a single line."""

    @staticmethod
    def _timestamp(record: LogRecord) -> str:
        return datetime.fromtimestamp(record.timestamp, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )


class SimpleFormatter(Formatter):
    """`2026-09-19 10:30:00 [INFO] app: message key=value`"""

    name = "simple"

    def format(self, record: LogRecord) -> str:
        line = (
            f"{self._timestamp(record)} [{record.level}] "
            f"{record.logger_name}: {record.message}"
        )
        if record.context:
            line += " " + " ".join(f"{k}={v}" for k, v in sorted(record.context.items()))
        return line


class JsonFormatter(Formatter):
    """One JSON object per line, for anything that will be parsed downstream."""

    name = "json"

    def format(self, record: LogRecord) -> str:
        payload = {
            "timestamp": record.timestamp,
            "level": str(record.level),
            "logger": record.logger_name,
            "message": record.message,
            **record.context,
        }
        return json.dumps(payload, default=str, sort_keys=True)


FORMATTERS: dict[str, type[Formatter]] = {
    SimpleFormatter.name: SimpleFormatter,
    JsonFormatter.name: JsonFormatter,
}


def get_formatter(name: str = "simple") -> Formatter:
    try:
        return FORMATTERS[name]()
    except KeyError:
        known = ", ".join(sorted(FORMATTERS))
        raise ValueError(f"{name!r} is not a formatter. Try one of: {known}") from None
