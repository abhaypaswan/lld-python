"""Runnable demo for the notification service.

python3 src/main.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from notification_service import (  # noqa: E402
    DeduplicatingChannel,
    EmailChannel,
    NotificationService,
    Priority,
    PushChannel,
    RateLimitedChannel,
    RecordingChannel,
    RetryingChannel,
    SlackChannel,
    SMSChannel,
    Subscriber,
)


class Clock:
    """A clock the demo can wind forward, so the windows are visible."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def build_service(clock) -> tuple[NotificationService, RecordingChannel]:
    # Email gets the full stack: dedupe innermost, then a per-recipient cap,
    # with retries outermost so a transient failure is re-checked against the
    # limiter on each attempt.
    email = RecordingChannel(
        RetryingChannel(
            RateLimitedChannel(
                DeduplicatingChannel(EmailChannel(), window=300, clock=clock),
                limit=3,
                window=60,
                clock=clock,
            ),
            attempts=2,
            sleep=lambda _: None,
        )
    )

    service = NotificationService()
    service.register_channel(email)
    service.register_channel(SMSChannel())
    service.register_channel(PushChannel())
    service.register_channel(SlackChannel())
    return service, email


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Run the notification service demo.").parse_args(argv)

    clock = Clock()
    service, email = build_service(clock)

    service.subscribe(
        Subscriber(
            "alice",
            addresses={"email": "alice@example.com", "sms": "+15550101", "push": "device-a"},
            # Alice wants everything by email, but only urgent things by text.
            minimum_priority={"sms": Priority.URGENT, "push": Priority.HIGH},
        )
    )
    service.subscribe(
        Subscriber("ops", addresses={"slack": "#ops-alerts", "email": "ops@example.com"})
    )

    service.on_delivery(lambda result: None)

    print("1. A normal notification. SMS is skipped: Alice set it to urgent-only.\n")
    for result in service.notify("alice", "Deploy finished", "Build 4021 is live."):
        print(f"   {result}")

    print("\n2. The same alert four times, as a flapping check would send it.\n")
    for i in range(4):
        results = service.notify("alice", "Disk usage high", channels=["email"])
        print(f"   attempt {i + 1}: {results[0]}")

    print("\n3. An urgent one. Now SMS and push both qualify.\n")
    for result in service.notify(
        "alice", "Database unreachable", "Primary is down.", priority=Priority.URGENT
    ):
        print(f"   {result}")

    print("\n4. A broadcast to everyone.\n")
    for user_id, results in service.broadcast("Maintenance at 02:00").items():
        for result in results:
            print(f"   {user_id}: {result}")

    print(f"\nEmail channel: {len(email.delivered)} delivered, {len(email.failed)} suppressed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
