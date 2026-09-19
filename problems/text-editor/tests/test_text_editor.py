"""Undo, redo, and the bugs that live between them."""

from dataclasses import FrozenInstanceError

import pytest
from text_editor import Document, Editor, InsertCommand
from text_editor.commands import CompositeCommand, DeleteCommand, ReplaceCommand
from text_editor.history import NothingToRedo, NothingToUndo


@pytest.fixture
def editor():
    return Editor()


@pytest.fixture
def loaded():
    return Editor("the quick brown fox")


# -- document -------------------------------------------------------------


def test_inserting_puts_text_at_a_position():
    document = Document("hello")
    document.insert(5, " world")

    assert document.content == "hello world"


def test_deleting_returns_what_it_removed():
    document = Document("hello world")

    assert document.delete(5, 11) == " world"
    assert document.content == "hello"


def test_a_backwards_range_is_put_the_right_way_round():
    """Dragging a selection right to left gives start > end."""
    document = Document("hello world")

    assert document.delete(11, 5) == " world"


def test_positions_are_clamped_rather_than_rejected():
    document = Document("hi")

    document.move_cursor(9999)

    assert document.cursor == 2


def test_a_negative_position_clamps_to_zero():
    document = Document("hi")

    assert document.move_cursor(-5) == 0


def test_selection_reads_back_the_selected_text():
    document = Document("hello world")
    document.select(6, 11)

    assert document.selected_text == "world"


# -- memento --------------------------------------------------------------


def test_a_snapshot_restores_content_and_cursor():
    document = Document("hello")
    document.move_cursor(2)
    state = document.snapshot()

    document.insert(5, " world")
    document.restore(state)

    assert document.content == "hello"
    assert document.cursor == 2


def test_a_snapshot_is_frozen():
    """A mutable snapshot of a mutable document is worth nothing."""
    state = Document("hello").snapshot()

    with pytest.raises(FrozenInstanceError):
        state.content = "tampered"


def test_editing_after_a_snapshot_does_not_change_it():
    document = Document("hello")
    state = document.snapshot()

    document.insert(0, "xxx")

    assert state.content == "hello"


# -- undo and redo --------------------------------------------------------


def test_undo_reverses_an_insert(editor):
    editor.insert(0, "hello")

    editor.undo()

    assert editor.content == ""


def test_undo_reverses_a_delete(loaded):
    loaded.delete(0, 4)
    assert loaded.content == "quick brown fox"

    loaded.undo()

    assert loaded.content == "the quick brown fox"


def test_undo_reverses_a_replace(loaded):
    loaded.replace(4, 9, "slow")

    loaded.undo()

    assert loaded.content == "the quick brown fox"


def test_redo_reapplies_an_undone_edit(editor):
    editor.insert(0, "hello")
    editor.undo()

    editor.redo()

    assert editor.content == "hello"


def test_undo_restores_the_cursor_too(loaded):
    loaded.move_cursor(4)
    loaded.insert(4, "very ")
    assert loaded.cursor == 9

    loaded.undo()

    assert loaded.cursor == 4


def test_many_edits_undo_in_reverse_order(editor):
    editor.insert(0, "a")
    editor.insert(1, "b")
    editor.insert(2, "c")

    editor.undo()
    editor.undo()

    assert editor.content == "a"


def test_undoing_everything_returns_the_original(loaded):
    loaded.insert(0, "xx")
    loaded.delete(5, 8)
    loaded.replace(0, 2, "yy")

    while loaded.can_undo:
        loaded.undo()

    assert loaded.content == "the quick brown fox"


def test_undo_on_an_empty_history_is_an_error(editor):
    with pytest.raises(NothingToUndo, match="nothing to undo"):
        editor.undo()


def test_redo_with_nothing_undone_is_an_error(editor):
    editor.insert(0, "hello")

    with pytest.raises(NothingToRedo, match="nothing to redo"):
        editor.redo()


# -- the rule everyone misses ---------------------------------------------


def test_a_new_edit_clears_the_redo_stack(editor):
    """Undo, then type: the future you were about to redo into is gone."""
    editor.insert(0, "hello")
    editor.undo()
    assert editor.can_redo

    editor.insert(0, "something else")

    assert not editor.can_redo, "redoing here would apply an edit to text it never saw"


def test_the_document_stays_correct_after_undo_then_a_new_edit(editor):
    editor.insert(0, "aaa")
    editor.insert(3, "bbb")
    editor.undo()
    editor.insert(3, "ccc")

    assert editor.content == "aaaccc"

    editor.undo()
    editor.undo()

    assert editor.content == ""


# -- coalescing -----------------------------------------------------------


def test_consecutive_typing_is_one_undo_step(editor):
    for character in "hello":
        editor.type(character)

    editor.undo()

    assert editor.content == "", "typing five characters should be one undo, not five"
    assert editor.history.depth == 0


def test_typing_that_is_not_consecutive_is_not_merged(editor):
    editor.type("hello")
    editor.move_cursor(0)
    editor.type("X")

    editor.undo()

    assert editor.content == "hello"


def test_a_newline_ends_a_coalescing_run(editor):
    editor.type("line one")
    editor.type("\n")
    editor.type("line two")

    editor.undo()

    assert editor.content == "line one\n"


def test_coalescing_stops_at_a_reasonable_length(editor):
    for _ in range(200):
        editor.type("x")

    assert editor.history.depth > 1, "one undo should not wipe out 200 characters"


def test_coalescing_can_be_turned_off():
    editor = Editor(coalesce=False)
    for character in "hello":
        editor.type(character)

    editor.undo()

    assert editor.content == "hell"


# -- composite ------------------------------------------------------------


def test_replace_all_is_a_single_undo_step(loaded):
    loaded.replace_all("o", "0")
    assert loaded.content == "the quick br0wn f0x"

    loaded.undo()

    assert loaded.content == "the quick brown fox"


def test_replace_all_handles_a_longer_replacement(loaded):
    loaded.replace_all("o", "OOO")

    assert loaded.content == "the quick brOOOwn fOOOx"

    loaded.undo()
    assert loaded.content == "the quick brown fox"


def test_replace_all_handles_a_shorter_replacement():
    editor = Editor("aaa bbb aaa")
    editor.replace_all("aaa", "x")

    assert editor.content == "x bbb x"

    editor.undo()
    assert editor.content == "aaa bbb aaa"


def test_replace_all_reports_nothing_when_there_is_no_match(loaded):
    assert loaded.replace_all("zebra", "x") is None
    assert not loaded.can_undo


def test_a_composite_undoes_in_reverse_order():
    """Each edit shifts the positions the later ones were computed against."""
    editor = Editor("abc")
    composite = CompositeCommand(
        [
            InsertCommand(0, "1"),
            InsertCommand(0, "2"),
        ]
    )
    editor.history.execute(composite)
    assert editor.content == "21abc"

    editor.undo()

    assert editor.content == "abc"


def test_the_undo_label_names_what_will_be_undone(loaded):
    loaded.replace_all("o", "0")

    assert loaded.history.undo_label == "Undo Replace 2 occurrences"


# -- find, clipboard ------------------------------------------------------


def test_find_returns_every_offset():
    assert Editor("abab").find("ab") == [0, 2]


def test_find_includes_overlapping_matches():
    assert Editor("aaaa").find("aa") == [0, 1, 2]


def test_find_on_an_empty_needle_returns_nothing(loaded):
    assert loaded.find("") == []


def test_copy_puts_the_selection_on_the_clipboard(loaded):
    loaded.select(4, 9)

    assert loaded.copy() == "quick"
    assert loaded.content == "the quick brown fox", "copy must not change the document"


def test_cut_removes_the_selection(loaded):
    loaded.select(4, 10)

    assert loaded.cut() == "quick "
    assert loaded.content == "the brown fox"


def test_cut_is_a_single_undo_step(loaded):
    loaded.select(4, 10)
    loaded.cut()

    loaded.undo()

    assert loaded.content == "the quick brown fox"


def test_paste_inserts_at_the_cursor(loaded):
    loaded.select(4, 9)
    loaded.copy()
    loaded.move_cursor(len(loaded))
    loaded.paste()

    assert loaded.content == "the quick brown foxquick"


def test_paste_replaces_the_selection(loaded):
    loaded.select(4, 9)
    loaded.copy()
    loaded.select(16, 19)
    loaded.paste()

    assert loaded.content == "the quick brown quick"


def test_pasting_an_empty_clipboard_does_nothing(loaded):
    assert loaded.paste() is None
    assert not loaded.can_undo


def test_typing_over_a_selection_replaces_it(loaded):
    loaded.select(4, 9)
    loaded.type("slow")

    assert loaded.content == "the slow brown fox"

    loaded.undo()
    assert loaded.content == "the quick brown fox"


def test_backspace_at_the_start_does_nothing(editor):
    editor.move_cursor(0)

    assert editor.backspace() is None


def test_backspace_removes_the_character_before_the_cursor():
    editor = Editor("hello")

    editor.backspace()

    assert editor.content == "hell"


# -- limits and checkpoints -----------------------------------------------


def test_the_undo_stack_is_bounded():
    """Unbounded undo is an unbounded leak in a long session."""
    editor = Editor(undo_limit=5, coalesce=False)
    for i in range(20):
        editor.insert(0, str(i % 10))

    assert editor.history.depth == 5


def test_the_oldest_history_is_what_gets_dropped():
    editor = Editor(undo_limit=2, coalesce=False)
    editor.insert(0, "a")
    editor.insert(1, "b")
    editor.insert(2, "c")

    editor.undo()
    editor.undo()

    assert editor.content == "a", "the insert of 'a' should no longer be undoable"
    assert not editor.can_undo


def test_a_checkpoint_can_be_restored(loaded):
    loaded.checkpoint("original")
    loaded.replace_all("o", "0")

    loaded.restore("original")

    assert loaded.content == "the quick brown fox"


def test_restoring_a_checkpoint_clears_the_history(loaded):
    loaded.checkpoint("original")
    loaded.insert(0, "xx")

    loaded.restore("original")

    assert not loaded.can_undo, "the stack describes a path the document is no longer on"


def test_an_unknown_checkpoint_lists_the_real_ones(loaded):
    loaded.checkpoint("first")

    with pytest.raises(KeyError, match="first"):
        loaded.restore("nope")


# -- command invariants ---------------------------------------------------


def test_a_command_cannot_be_undone_before_it_runs():
    with pytest.raises(RuntimeError, match="never executed"):
        InsertCommand(0, "x").undo(Document())


def test_delete_captures_the_removed_text_when_it_runs():
    """Capturing at construction would read the document in the wrong state."""
    document = Document("hello")
    command = DeleteCommand(0, 5)

    document.insert(0, "xxx")
    command.execute(document)

    assert command.removed == "xxxhe"


def test_replace_round_trips_through_undo():
    document = Document("hello world")
    command = ReplaceCommand(6, 11, "there")
    command.execute(document)
    assert document.content == "hello there"

    command.undo(document)

    assert document.content == "hello world"
