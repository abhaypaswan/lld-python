"""Routing, and the rules only the mediator is in a position to apply."""

import pytest
from chat_room import ChatServer, Message, MessageType, NotInRoom, User


@pytest.fixture
def clock():
    return lambda: 0.0


@pytest.fixture
def server(clock):
    return ChatServer(clock=clock)


@pytest.fixture
def room(server):
    return server.create_room("general")


@pytest.fixture
def people(server, room):
    users = [server.register(name) for name in ("alice", "bob", "carol")]
    for user in users:
        room.join(user)
    return users


# -- the pattern itself ---------------------------------------------------


def test_a_user_holds_no_reference_to_another_user(people):
    """The absence is the design. Colleagues know the mediator, not each other."""
    alice = people[0]

    assert not any(isinstance(value, User) for value in vars(alice).values())


def test_a_user_only_knows_the_rooms_it_is_in(people, room):
    assert people[0].rooms == ["general"]


def test_a_message_carries_a_name_not_a_sender_object(people, room):
    people[0].send(room, "hello")

    assert isinstance(room.history[-1].sender, str)


# -- broadcasting ---------------------------------------------------------


def test_a_message_reaches_everyone_else(people, room):
    alice, bob, carol = people

    delivery = alice.send(room, "hello")

    assert set(delivery.delivered_to) == {"bob", "carol"}


def test_the_sender_does_not_receive_their_own_message(people, room):
    alice, _, _ = people
    before = len(alice.inbox)

    alice.send(room, "hello")

    assert len(alice.inbox) == before


def test_everyone_receives_the_same_message_object(people, room):
    alice, bob, carol = people
    alice.send(room, "hello")

    assert bob.inbox[-1] is carol.inbox[-1]


def test_an_empty_message_is_refused():
    with pytest.raises(ValueError, match="cannot be empty"):
        Message("alice", "   ")


def test_someone_outside_the_room_cannot_send(server, room):
    outsider = server.register("dave")

    with pytest.raises(NotInRoom, match="not in general"):
        outsider.send(room, "hello")


# -- joining and leaving --------------------------------------------------


def test_joining_announces_to_the_others(server, room):
    alice = server.register("alice")
    bob = server.register("bob")
    room.join(alice)

    room.join(bob)

    assert "bob joined general" in alice.transcript()[-1]


def test_a_joiner_does_not_see_their_own_arrival_notice(server, room):
    alice = server.register("alice")
    room.join(alice)
    bob = server.register("bob")

    room.join(bob)

    assert not any("bob joined" in line for line in bob.transcript())


def test_a_joiner_gets_the_backlog(server, room):
    alice = server.register("alice")
    room.join(alice)
    alice.send(room, "said before you arrived")

    bob = server.register("bob")
    room.join(bob)

    assert any("said before you arrived" in line for line in bob.transcript())


def test_leaving_announces_it(people, room):
    alice, bob, _ = people

    alice.send(room, "bye")
    room.leave(alice)

    assert "alice left general" in bob.transcript()[-1]


def test_someone_who_left_receives_nothing_more(people, room):
    alice, bob, _ = people
    room.leave(alice)
    before = len(alice.inbox)

    bob.send(room, "still here?")

    assert len(alice.inbox) == before


def test_joining_twice_is_an_error(people, room):
    with pytest.raises(ValueError, match="already in general"):
        room.join(people[0])


def test_leaving_a_room_you_are_not_in_is_an_error(server, room):
    with pytest.raises(NotInRoom, match="not in general"):
        room.leave(server.register("dave"))


# -- blocking -------------------------------------------------------------


def test_a_blocked_sender_is_withheld(people, room):
    alice, bob, carol = people
    carol.block("alice")

    delivery = alice.send(room, "hello")

    assert delivery.delivered_to == ("bob",)
    assert delivery.withheld_from == ("carol",)


def test_a_blocked_message_never_reaches_the_blocker(people, room):
    alice, _, carol = people
    carol.block("alice")
    before = len(carol.inbox)

    alice.send(room, "hello")

    assert len(carol.inbox) == before


def test_blocking_does_not_stop_anyone_else(people, room):
    alice, bob, carol = people
    carol.block("alice")

    assert bob.inbox[-1] if alice.send(room, "hello") else False


def test_a_block_is_enforced_by_the_room_not_the_sender(people, room):
    """The sender must not learn who blocked them."""
    alice, _, carol = people
    carol.block("alice")

    delivery = alice.send(room, "hello")

    assert delivery.reach == 1, "the send still succeeds, it just reaches fewer people"


def test_unblocking_restores_delivery(people, room):
    alice, _, carol = people
    carol.block("alice")
    carol.unblock("alice")

    assert "carol" in alice.send(room, "hello").delivered_to


def test_you_cannot_block_yourself(people):
    with pytest.raises(ValueError, match="cannot block yourself"):
        people[0].block("alice")


# -- direct messages ------------------------------------------------------


def test_a_direct_message_reaches_only_its_recipient(people, room):
    alice, bob, carol = people
    before = len(carol.inbox)

    delivery = alice.whisper(room, "bob", "just for you")

    assert delivery.delivered_to == ("bob",)
    assert len(carol.inbox) == before


def test_a_direct_message_stays_out_of_the_transcript(people, room):
    """Recording it would leak a private message to everyone who joins later."""
    alice, _, _ = people

    alice.whisper(room, "bob", "just for you")

    assert not any("just for you" in line for line in room.transcript())


def test_a_direct_message_to_someone_absent_is_an_error(people, room):
    with pytest.raises(NotInRoom, match="dave is not in general"):
        people[0].whisper(room, "dave", "hello")


def test_a_direct_message_respects_a_block(people, room):
    alice, bob, _ = people
    bob.block("alice")

    delivery = alice.whisper(room, "bob", "hello")

    assert not delivery
    assert "blocked" in delivery.reason


def test_a_direct_message_needs_a_recipient():
    with pytest.raises(ValueError, match="needs a recipient"):
        Message("alice", "hi", MessageType.DIRECT)


# -- moderation -----------------------------------------------------------


def test_a_muted_user_reaches_nobody(people, room):
    alice, bob, _ = people
    room.mute("alice")
    before = len(bob.inbox)

    delivery = alice.send(room, "hello")

    assert not delivery
    assert "muted" in delivery.reason
    assert len(bob.inbox) == before


def test_unmuting_restores_sending(people, room):
    alice, _, _ = people
    room.mute("alice")
    room.unmute("alice")

    assert alice.send(room, "hello")


def test_a_banned_word_blocks_the_message(people, room):
    alice, _, _ = people
    room.ban_word("spoiler")

    delivery = alice.send(room, "here is a SPOILER for you")

    assert not delivery
    assert "spoiler" in delivery.reason


def test_a_refused_message_is_not_recorded(people, room):
    alice, _, _ = people
    room.mute("alice")
    before = len(room.history)

    alice.send(room, "hello")

    assert len(room.history) == before


# -- history --------------------------------------------------------------


def test_the_transcript_records_what_was_said(people, room):
    people[0].send(room, "hello")

    assert "<alice> hello" in room.transcript()


def test_the_transcript_is_bounded(server):
    room = server.create_room("busy", history_limit=5)
    alice = server.register("alice")
    room.join(alice)

    for i in range(20):
        alice.send(room, f"message {i}")

    assert len(room.history) == 5


def test_the_oldest_history_is_dropped_first(server):
    room = server.create_room("busy", history_limit=3)
    alice = server.register("alice")
    room.join(alice)
    for i in range(5):
        alice.send(room, f"message {i}")

    assert "message 0" not in " ".join(room.transcript())
    assert "message 4" in " ".join(room.transcript())


# -- several rooms --------------------------------------------------------


def test_rooms_are_independent(server):
    alice = server.register("alice")
    bob = server.register("bob")
    carol = server.register("carol")

    general = server.create_room("general")
    random = server.create_room("random")
    for user in (alice, bob):
        general.join(user)
    for user in (alice, carol):
        random.join(user)

    before = len(carol.inbox)
    alice.send(general, "only in general")

    assert len(carol.inbox) == before


def test_a_user_can_be_in_several_rooms(server):
    alice = server.register("alice")
    for name in ("general", "random"):
        server.create_room(name).join(alice)

    assert alice.rooms == ["general", "random"]


def test_a_server_broadcast_reaches_every_room(server):
    alice = server.register("alice")
    bob = server.register("bob")
    server.create_room("general").join(alice)
    server.create_room("random").join(bob)

    server.broadcast("server restarting")

    assert "server restarting" in alice.transcript()[-1]
    assert "server restarting" in bob.transcript()[-1]


def test_an_unknown_user_lists_the_registered_ones(server):
    server.register("alice")

    with pytest.raises(KeyError, match="alice"):
        server.user("nobody")


def test_an_unknown_room_lists_the_real_ones(server):
    server.create_room("general")

    with pytest.raises(KeyError, match="general"):
        server.room("nowhere")


def test_a_name_cannot_be_registered_twice(server):
    server.register("alice")

    with pytest.raises(ValueError, match="already registered"):
        server.register("alice")


def test_a_user_needs_a_name():
    with pytest.raises(ValueError, match="needs a name"):
        User("   ")


# -- presence -------------------------------------------------------------


def test_online_members_exclude_those_who_went_offline(people, room):
    people[0].go_offline()

    assert room.online_members == ["bob", "carol"]
    assert room.members == ["alice", "bob", "carol"]


def test_an_offline_user_still_receives_into_their_inbox(people, room):
    """Offline is a presence indicator, not a delivery filter."""
    alice, bob, _ = people
    bob.go_offline()

    alice.send(room, "hello")

    assert "hello" in bob.transcript()[-1]
