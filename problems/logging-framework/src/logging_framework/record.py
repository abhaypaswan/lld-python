"""One log event, as data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LogRecord:
    """Everything known about one log call.

    A record rather than a formatted string, because the handler at the end of
    the chain is what decides the format. Formatting at the call site throws
    away the structure a JSON sink needs.
    """

    level: Any
    message: str
    logger_name: str = "root"
    timestamp: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)

    def with_context(self, **extra: Any) -> LogRecord:
        """A copy carrying additional fields. The record itself stays frozen."""
        from dataclasses import replace

        return replace(self, context={**self.context, **extra})
