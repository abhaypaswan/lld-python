"""The logger, and the registry that hands them out."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from .handlers import Handler
from .level import LogLevel
from .record import LogRecord


class Logger:
    """What application code calls.

    Holds a level and the head of a handler chain. The level check happens here,
    before the record is built, so a disabled DEBUG call costs one integer
    comparison rather than a record allocation and a walk down the chain.
    """

    def __init__(
        self,
        name: str = "root",
        level: LogLevel | str = LogLevel.INFO,
        handler: Handler | None = None,
        clock: Callable[[], float] = time.time,
        parent: Logger | None = None,
    ):
        self.name = name
        self.level = LogLevel.parse(level)
        self.handler = handler
        self.clock = clock
        self.parent = parent
        self.context: dict = {}

    # -- configuration ----------------------------------------------------

    def add_handler(self, handler: Handler) -> Handler:
        """Append to the end of this logger's chain."""
        if self.handler is None:
            self.handler = handler
            return handler

        tail = self.handler
        while tail.next_handler is not None:
            tail = tail.next_handler
        tail.set_next(handler)
        return handler

    def set_level(self, level: LogLevel | str) -> None:
        self.level = LogLevel.parse(level)

    def bind(self, **context) -> Logger:
        """A child logger that stamps every record with extra fields.

        `log.bind(request_id="abc")` gives you a logger whose every record
        carries that id, without threading it through every call site.
        """
        child = Logger(self.name, self.level, self.handler, self.clock, parent=self)
        child.context = {**self.context, **context}
        return child

    # -- logging ----------------------------------------------------------

    def log(self, level: LogLevel | str, message: str, **context) -> LogRecord | None:
        level = LogLevel.parse(level)

        # The cheap check first. Everything below this line costs real work.
        if level < self.level:
            return None

        record = LogRecord(
            level=level,
            message=message,
            logger_name=self.name,
            timestamp=self.clock(),
            context={**self.context, **context},
        )

        handler = self.handler
        if handler is not None:
            handler.handle(record)
        return record

    def debug(self, message: str, **context):
        return self.log(LogLevel.DEBUG, message, **context)

    def info(self, message: str, **context):
        return self.log(LogLevel.INFO, message, **context)

    def warning(self, message: str, **context):
        return self.log(LogLevel.WARNING, message, **context)

    def error(self, message: str, **context):
        return self.log(LogLevel.ERROR, message, **context)

    def fatal(self, message: str, **context):
        return self.log(LogLevel.FATAL, message, **context)

    def close(self) -> None:
        handler = self.handler
        while handler is not None:
            handler.close()
            handler = handler.next_handler


class LoggerRegistry:
    """Singleton: one registry of named loggers per process.

    Singleton is the right call here for the reason it is usually the wrong
    one -- the thing being shared is genuinely global. Two registries would mean
    `get_logger("app")` returning different loggers depending on which module
    asked, and configuration applied in one place not taking effect in another.

    The double-checked lock makes the first call safe from several threads. The
    cheap read outside the lock keeps every subsequent call off it.

    It is worth saying in an interview that this makes the registry hard to
    isolate in tests, which is why `reset()` exists and why `Logger` itself is
    an ordinary class you can construct directly.
    """

    _instance: LoggerRegistry | None = None
    _lock = threading.Lock()

    def __new__(cls) -> LoggerRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._loggers = {}
                    instance._default_level = LogLevel.INFO
                    instance._default_handler = None
                    cls._instance = instance
        return cls._instance

    def get_logger(self, name: str = "root") -> Logger:
        logger = self._loggers.get(name)
        if logger is None:
            logger = Logger(name, self._default_level, self._default_handler)
            self._loggers[name] = logger
        return logger

    def configure(self, level: LogLevel | str | None = None, handler: Handler | None = None):
        """Set the defaults, and apply them to loggers already handed out."""
        if level is not None:
            self._default_level = LogLevel.parse(level)
        if handler is not None:
            self._default_handler = handler

        for logger in self._loggers.values():
            if level is not None:
                logger.set_level(self._default_level)
            if handler is not None:
                logger.handler = handler
        return self

    @property
    def names(self) -> list[str]:
        return sorted(self._loggers)

    def reset(self) -> None:
        """Forget every logger. Exists so tests are not order-dependent."""
        for logger in self._loggers.values():
            logger.close()
        self._loggers.clear()
        self._default_level = LogLevel.INFO
        self._default_handler = None


def get_logger(name: str = "root") -> Logger:
    """The function application code actually calls."""
    return LoggerRegistry().get_logger(name)
