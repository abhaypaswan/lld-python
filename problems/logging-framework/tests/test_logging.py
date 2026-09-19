"""The handler chain, the level filtering, and the registry."""

import io
import json

import pytest
from logging_framework import (
    ConsoleHandler,
    FileHandler,
    Logger,
    LoggerRegistry,
    LogLevel,
    MemoryHandler,
    get_logger,
)
from logging_framework.formatters import JsonFormatter, get_formatter
from logging_framework.handlers import build_chain


@pytest.fixture
def clock():
    return lambda: 0.0


@pytest.fixture
def memory():
    return MemoryHandler("debug")


@pytest.fixture
def logger(memory, clock):
    return Logger("app", "debug", memory, clock=clock)


@pytest.fixture(autouse=True)
def clean_registry():
    """The registry is a singleton, so tests must not inherit each other's state."""
    LoggerRegistry().reset()
    yield
    LoggerRegistry().reset()


# -- levels ---------------------------------------------------------------


def test_levels_compare_by_severity():
    assert LogLevel.DEBUG < LogLevel.INFO < LogLevel.WARNING < LogLevel.ERROR < LogLevel.FATAL


def test_a_message_below_the_level_is_dropped(logger, memory):
    logger.set_level("warning")

    logger.debug("quiet")
    logger.info("also quiet")
    logger.warning("loud")

    assert len(memory.lines) == 1
    assert "loud" in memory.lines[0]


def test_a_dropped_message_never_becomes_a_record(logger):
    logger.set_level("error")

    assert logger.info("skipped") is None, "the level check must come before the work"


def test_an_unknown_level_name_lists_the_real_ones():
    with pytest.raises(ValueError, match="debug, info"):
        LogLevel.parse("verbose")


# -- the chain ------------------------------------------------------------


def test_every_handler_in_the_chain_sees_the_record(clock):
    first, second, third = (MemoryHandler("debug") for _ in range(3))
    logger = Logger("app", "debug", build_chain(first, second, third), clock=clock)

    logger.info("hello")

    assert len(first.lines) == len(second.lines) == len(third.lines) == 1


def test_each_handler_applies_its_own_threshold(clock):
    everything = MemoryHandler("debug")
    problems_only = MemoryHandler("error")
    logger = Logger("app", "debug", build_chain(everything, problems_only), clock=clock)

    logger.debug("d")
    logger.info("i")
    logger.error("e")

    assert len(everything.lines) == 3
    assert len(problems_only.lines) == 1


def test_a_handler_that_skips_a_record_still_passes_it_on(clock):
    """Logging is not the textbook 'first handler wins' chain, and shouldn't be."""
    strict = MemoryHandler("fatal")
    permissive = MemoryHandler("debug")
    logger = Logger("app", "debug", build_chain(strict, permissive), clock=clock)

    logger.info("hello")

    assert strict.lines == []
    assert len(permissive.lines) == 1, "the record must continue past a handler that ignored it"


def test_add_handler_appends_to_the_end_of_the_chain(logger, clock):
    second = MemoryHandler("debug")
    logger.add_handler(second)

    logger.info("hello")

    assert len(second.lines) == 1


def test_a_logger_with_no_handlers_does_not_crash(clock):
    assert Logger("app", "debug", None, clock=clock).info("into the void") is not None


def test_build_chain_with_nothing_returns_nothing():
    assert build_chain() is None


# -- formatters -----------------------------------------------------------


def test_the_simple_formatter_includes_level_logger_and_message(logger, memory):
    logger.info("started")

    assert "[INFO]" in memory.lines[0]
    assert "app: started" in memory.lines[0]


def test_context_is_appended_to_the_simple_format(logger, memory):
    logger.info("request", user="alice", status=200)

    assert "status=200 user=alice" in memory.lines[0]


def test_the_json_formatter_produces_parseable_lines(clock):
    handler = MemoryHandler("debug", formatter=JsonFormatter())
    Logger("app", "debug", handler, clock=clock).error("boom", user="alice")

    payload = json.loads(handler.lines[0])

    assert payload["level"] == "ERROR"
    assert payload["message"] == "boom"
    assert payload["user"] == "alice"


def test_two_handlers_can_format_the_same_record_differently(clock):
    plain = MemoryHandler("debug", formatter="simple")
    structured = MemoryHandler("debug", formatter="json")
    Logger("app", "debug", build_chain(plain, structured), clock=clock).info("hello")

    assert not plain.lines[0].startswith("{")
    assert json.loads(structured.lines[0])["message"] == "hello"


def test_an_unknown_formatter_lists_the_known_ones():
    with pytest.raises(ValueError, match="json, simple"):
        get_formatter("xml")


# -- bound context --------------------------------------------------------


def test_bind_stamps_every_record_from_the_child(logger, memory):
    request_log = logger.bind(request_id="r-1")

    request_log.info("start")
    request_log.info("finish")

    assert all("request_id=r-1" in line for line in memory.lines)


def test_bind_does_not_touch_the_parent(logger, memory):
    logger.bind(request_id="r-1").info("child")
    logger.info("parent")

    assert "request_id" in memory.lines[0]
    assert "request_id" not in memory.lines[1]


def test_a_per_call_field_beats_a_bound_one(logger, memory):
    logger.bind(user="alice").info("switch", user="bob")

    assert "user=bob" in memory.lines[0]


# -- handlers -------------------------------------------------------------


def test_the_console_handler_sends_warnings_to_stderr(clock):
    out, err = io.StringIO(), io.StringIO()
    handler = ConsoleHandler("debug", stream=out, error_stream=err)
    logger = Logger("app", "debug", handler, clock=clock)

    logger.info("fine")
    logger.error("broken")

    assert "fine" in out.getvalue() and "broken" not in out.getvalue()
    assert "broken" in err.getvalue()


def test_the_console_split_point_is_configurable(clock):
    out, err = io.StringIO(), io.StringIO()
    handler = ConsoleHandler("debug", stream=out, error_stream=err, split_at="fatal")
    Logger("app", "debug", handler, clock=clock).error("broken")

    assert "broken" in out.getvalue()


def test_the_file_handler_writes_lines(tmp_path, clock):
    path = tmp_path / "logs" / "app.log"
    logger = Logger("app", "debug", FileHandler(path), clock=clock)

    logger.info("first")
    logger.info("second")
    logger.close()

    assert path.read_text().splitlines() == [
        "1970-01-01 00:00:00 [INFO] app: first",
        "1970-01-01 00:00:00 [INFO] app: second",
    ]


def test_the_file_handler_does_not_create_a_file_it_never_writes_to(tmp_path, clock):
    path = tmp_path / "app.log"
    logger = Logger("app", "error", FileHandler(path), clock=clock)

    logger.info("below the logger's level")
    logger.close()

    assert not path.exists()


def test_the_memory_handler_can_be_bounded(clock):
    handler = MemoryHandler("debug", capacity=3)
    logger = Logger("app", "debug", handler, clock=clock)

    for i in range(10):
        logger.info(f"message {i}")

    assert len(handler.lines) == 3
    assert "message 9" in handler.lines[-1]


def test_closing_twice_is_safe(tmp_path, clock):
    logger = Logger("app", "debug", FileHandler(tmp_path / "a.log"), clock=clock)
    logger.info("hello")

    logger.close()
    logger.close()


# -- the registry ---------------------------------------------------------


def test_the_registry_is_a_singleton():
    assert LoggerRegistry() is LoggerRegistry()


def test_the_same_name_gives_back_the_same_logger():
    assert get_logger("app") is get_logger("app")


def test_different_names_give_different_loggers():
    assert get_logger("app") is not get_logger("db")


def test_configure_reaches_loggers_already_handed_out():
    existing = get_logger("app")
    handler = MemoryHandler("debug")

    LoggerRegistry().configure(level="debug", handler=handler)
    existing.debug("now visible")

    assert len(handler.lines) == 1


def test_configure_applies_to_loggers_created_afterwards():
    handler = MemoryHandler("debug")
    LoggerRegistry().configure(level="debug", handler=handler)

    get_logger("new").debug("visible")

    assert len(handler.lines) == 1


def test_reset_forgets_every_logger():
    get_logger("app")
    LoggerRegistry().reset()

    assert LoggerRegistry().names == []
