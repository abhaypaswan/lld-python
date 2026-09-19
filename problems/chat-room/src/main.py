"""Runnable demo for the chat room.

python3 src/main.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chat_room import ChatServer  # noqa: E402


def coupling(n: int) -> tuple[int, int]:
    """References to maintain: direct peer links, versus one mediator each."""
    return n * (n - 1), n


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Run the chat room demo.").parse_args(argv)

    clock = [0.0]
    server = ChatServer(clock=lambda: clock[0])

    alice = server.register("alice")
    bob = server.register("bob")
    carol = server.register("carol")
    dave = server.register("dave")

    general = server.create_room("general")
    random = server.create_room("random")

    print("1. Four people join #general. Each knows the room, not each other.\n")
    for user in (alice, bob, carol, dave):
        general.join(user)
    print(f"   members: {', '.join(general.members)}")

    direct, mediated = coupling(len(general))
    print(f"   peer-to-peer would need {direct} references; the mediator needs {mediated}")

    print("\n2. A broadcast reaches everyone except the sender.\n")
    print(f"   {alice.send(general, 'morning all')}")
    print(f"   bob sees: {bob.transcript()[-1]}")

    print("\n3. carol blocks alice. The room enforces it; alice is not told who.\n")
    carol.block("alice")
    delivery = alice.send(general, "anyone up for lunch?")
    print(f"   {delivery}")
    print(f"   bob sees:   {bob.transcript()[-1]}")
    print(f"   carol sees: {carol.transcript()[-1]}   <- unchanged")

    print("\n4. A direct message goes to one person, and stays out of history.\n")
    print(f"   {bob.whisper(general, 'dave', 'want to grab coffee?')}")
    print(f"   dave sees:  {dave.transcript()[-1]}")
    print(f"   in transcript: {any('coffee' in line for line in general.transcript())}")

    print("\n5. Moderation lives in the room, because it is about a relationship.\n")
    general.ban_word("spoiler")
    print(f"   {alice.send(general, 'big SPOILER coming')}")
    general.mute("dave")
    print(f"   {dave.send(general, 'hello?')}")

    print("\n6. Rooms are independent, and a late joiner gets the backlog.\n")
    for user in (alice, carol):
        random.join(user)
    alice.send(random, "only in #random")
    print(
        f"   bob is in {bob.rooms}, so he did not see it: "
        f"{not any('only in #random' in m for m in bob.transcript())}"
    )

    eve = server.register("eve")
    general.join(eve)
    print(f"   eve joined #general late and received {len(eve.inbox)} backlog messages")

    print("\n7. A server-wide announcement, room by room.\n")
    for room_name, result in server.broadcast("server restarting in 5 minutes").items():
        print(f"   #{room_name:<8} {result}")

    print(f"\n#general transcript ({len(general.history)} messages):\n")
    for line in general.transcript():
        print(f"   {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
