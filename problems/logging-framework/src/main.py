"""Runnable demo for the logging framework.

python3 src/main.py
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from logging_framework import (  # noqa: E402
    ConsoleHandler,
    FileHandler,
    LoggerRegistry,
    MemoryHandler,
    get_logger,
)
from logging_framework.formatters import JsonFormatter  # noqa: E402
from logging_framework.handlers import build_chain  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Run the logging framework demo.").parse_args(argv)

    log_dir = Path(tempfile.mkdtemp(prefix="lld-logging-"))
    errors_path = log_dir / "errors.jsonl"

    # One chain, three destinations, three different thresholds and formats:
    #   console  DEBUG and up, human-readable
    #   file     ERROR and up, JSON for a log pipeline
    #   memory   everything, so we can count at the end
    audit = MemoryHandler("debug")
    chain = build_chain(
        ConsoleHandler("debug"),
        FileHandler(errors_path, level="error", formatter=JsonFormatter()),
        audit,
    )

    LoggerRegistry().configure(level="debug", handler=chain)

    app = get_logger("app")
    db = get_logger("db")

    app.info("Service starting", version="1.4.2")
    app.debug("Config loaded", source="env")

    # bind() gives a child logger that stamps every record, so the request id
    # does not have to be threaded through every call.
    request = app.bind(request_id="req-8814", user="alice")
    request.info("GET /orders")
    request.warning("Slow query", duration_ms=1240)
    request.error("Upstream timeout", upstream="payments", status=504)

    db.error("Connection pool exhausted", size=20, waiting=7)
    app.info("Service ready")

    print(f"\n{len(audit.lines)} records passed through the chain.")
    print(f"{len(errors_path.read_text().splitlines())} of them reached {errors_path}:\n")
    print(errors_path.read_text().rstrip())

    LoggerRegistry().reset()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
