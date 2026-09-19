"""The composite tree, the visitors over it, and path resolution."""

import pytest
from file_system import Directory, File, FileSystem, NotADirectory, PathNotFound
from file_system.visitors import DiskUsageVisitor, FindVisitor


@pytest.fixture
def fs():
    filesystem = FileSystem()
    filesystem.write("/src/app/main.py", "print('hello')")
    filesystem.write("/src/app/util.py", "x = 1")
    filesystem.write("/src/test_app.py", "assert True")
    filesystem.write("/README.md", "# Project")
    filesystem.mkdir("/empty")
    return filesystem


# -- composite ------------------------------------------------------------


def test_a_file_and_a_directory_both_answer_size():
    """The point of Composite: the caller never asks which it is holding."""
    nodes = [File("a.txt", "hello"), Directory("d")]

    assert [node.size for node in nodes] == [5, 0]


def test_a_directory_size_is_the_sum_of_everything_under_it():
    root = Directory()
    inner = root.add(Directory("inner"))
    root.add(File("a.txt", "12345"))
    inner.add(File("b.txt", "123"))
    inner.add(File("c.txt", "12"))

    assert root.size == 10


def test_size_is_recomputed_after_a_write():
    root = Directory()
    file = root.add(File("a.txt", "12345"))

    file.write("1")

    assert root.size == 1, "a cached size would still say 5"


def test_paths_are_built_from_the_parent_chain():
    root = Directory()
    deep = root.add(Directory("a")).add(Directory("b")).add(File("c.txt"))

    assert deep.path == "/a/b/c.txt"


def test_a_node_directly_under_the_root_has_a_single_slash():
    root = Directory()

    assert root.add(File("a.txt")).path == "/a.txt"


def test_the_root_path_is_a_slash():
    assert Directory().path == "/"


def test_depth_counts_ancestors():
    root = Directory()
    inner = root.add(Directory("a")).add(Directory("b"))

    assert (root.depth, inner.depth) == (0, 2)


def test_two_children_cannot_share_a_name():
    root = Directory()
    root.add(File("a.txt"))

    with pytest.raises(FileExistsError, match="already contains"):
        root.add(File("a.txt"))


def test_a_directory_cannot_contain_itself():
    root = Directory("d")

    with pytest.raises(ValueError, match="cannot contain itself"):
        root.add(root)


def test_a_directory_cannot_be_added_into_its_own_descendant():
    """Without this the tree grows a cycle and size() never returns."""
    root = Directory()
    a = root.add(Directory("a"))
    b = a.add(Directory("b"))

    with pytest.raises(ValueError, match="own descendant"):
        b.add(a)


def test_removing_a_node_detaches_it():
    root = Directory()
    file = root.add(File("a.txt"))

    root.remove("a.txt")

    assert file.parent is None
    assert "a.txt" not in root


def test_removing_something_absent_is_an_error():
    with pytest.raises(FileNotFoundError, match="contains no"):
        Directory().remove("nope.txt")


@pytest.mark.parametrize("name", ["", "   ", "a/b", ".", ".."])
def test_bad_names_are_rejected(name):
    with pytest.raises(ValueError):
        File(name)


def test_only_the_root_may_have_an_empty_name():
    Directory()  # fine

    with pytest.raises(ValueError, match="cannot be empty"):
        File("")


# -- iteration ------------------------------------------------------------


def test_listing_puts_directories_before_files():
    root = Directory()
    root.add(File("z.txt"))
    root.add(Directory("a"))

    assert [n.name for n in root] == ["a", "z.txt"]


def test_walk_reaches_every_descendant(fs):
    names = {node.name for node in fs.root.walk()}

    assert {"src", "app", "main.py", "util.py", "README.md", "empty"} <= names


def test_walk_is_lazy(fs):
    """A deep tree should not be materialised just to find the first match."""
    walker = fs.root.walk()

    assert next(walker) is not None


def test_files_yields_only_files(fs):
    assert all(not node.is_directory for node in fs.root.files())


# -- path resolution ------------------------------------------------------


def test_a_path_resolves_to_its_node(fs):
    assert fs.resolve("/src/app/main.py").name == "main.py"


def test_a_missing_path_says_so(fs):
    with pytest.raises(PathNotFound, match="No such file or directory"):
        fs.resolve("/src/nope.py")


def test_descending_into_a_file_is_an_error(fs):
    with pytest.raises(NotADirectory, match="is a file"):
        fs.resolve("/README.md/inner")


def test_dot_segments_are_ignored(fs):
    assert fs.resolve("/src/./app/./main.py").name == "main.py"


def test_double_dot_goes_up(fs):
    assert fs.resolve("/src/app/../test_app.py").name == "test_app.py"


def test_double_dot_cannot_escape_the_root(fs):
    assert fs.resolve("/../../..") is fs.root


def test_trailing_and_repeated_slashes_are_harmless(fs):
    assert fs.resolve("//src///app//") is fs.resolve("/src/app")


# -- commands -------------------------------------------------------------


def test_mkdir_creates_a_directory(fs):
    fs.mkdir("/src/newdir")

    assert fs.exists("/src/newdir")


def test_mkdir_without_parents_needs_them_to_exist(fs):
    with pytest.raises(PathNotFound, match="No such directory"):
        fs.mkdir("/a/b/c")


def test_mkdir_with_parents_creates_the_whole_chain(fs):
    fs.mkdir("/a/b/c", parents=True)

    assert fs.exists("/a/b/c")


def test_mkdir_p_on_an_existing_directory_succeeds(fs):
    assert fs.mkdir("/src", parents=True) is fs.resolve("/src")


def test_mkdir_on_an_existing_directory_is_an_error(fs):
    with pytest.raises(FileExistsError, match="already exists"):
        fs.mkdir("/src")


def test_read_returns_what_was_written(fs):
    assert fs.read("/src/app/main.py") == "print('hello')"


def test_reading_a_directory_is_an_error(fs):
    with pytest.raises(IsADirectoryError, match="is a directory"):
        fs.read("/src")


def test_ls_marks_directories(fs):
    assert set(fs.ls("/src")) == {"app/", "test_app.py"}


def test_rm_removes_a_file(fs):
    fs.rm("/README.md")

    assert not fs.exists("/README.md")


def test_rm_refuses_a_non_empty_directory(fs):
    with pytest.raises(ValueError, match="not empty"):
        fs.rm("/src")


def test_rm_recursive_removes_the_whole_subtree(fs):
    fs.rm("/src", recursive=True)

    assert not fs.exists("/src/app/main.py")


def test_rm_allows_an_empty_directory(fs):
    fs.rm("/empty")

    assert not fs.exists("/empty")


def test_the_root_cannot_be_removed(fs):
    with pytest.raises(ValueError, match="Cannot remove the root"):
        fs.rm("/")


def test_move_relocates_a_node(fs):
    fs.move("/README.md", "/src/README.md")

    assert fs.exists("/src/README.md")
    assert not fs.exists("/README.md")


def test_move_can_rename(fs):
    fs.move("/README.md", "/READ.md")

    assert fs.read("/READ.md") == "# Project"


def test_a_move_onto_an_existing_name_is_refused(fs):
    with pytest.raises(FileExistsError, match="already exists"):
        fs.move("/README.md", "/src/test_app.py")


def test_a_refused_move_leaves_the_node_where_it_was(fs):
    with pytest.raises(FileExistsError):
        fs.move("/README.md", "/src/test_app.py")

    assert fs.exists("/README.md"), "a failed move must not orphan the node"


def test_moving_a_directory_takes_its_contents(fs):
    fs.mkdir("/archive")
    fs.move("/src", "/archive/src")

    assert fs.read("/archive/src/app/main.py") == "print('hello')"


# -- visitors -------------------------------------------------------------


def test_disk_usage_totals_the_tree(fs):
    usage = fs.du()

    assert usage.total_bytes == fs.size("/")
    assert usage.file_count == 4


def test_disk_usage_groups_by_extension(fs):
    usage = fs.du()

    assert set(usage.by_extension) == {"py", "md"}


def test_disk_usage_can_start_anywhere(fs):
    assert fs.du("/src/app").file_count == 2


def test_find_by_extension(fs):
    assert sorted(fs.find(extension="py")) == [
        "/src/app/main.py",
        "/src/app/util.py",
        "/src/test_app.py",
    ]


def test_find_by_name(fs):
    assert fs.find(name="main.py") == ["/src/app/main.py"]


def test_find_takes_an_arbitrary_predicate(fs):
    big = fs.find(predicate=lambda node: not node.is_directory and node.size > 10)

    assert "/src/app/main.py" in big


def test_find_returns_nothing_when_nothing_matches(fs):
    assert fs.find(extension="rs") == []


def test_a_visitor_never_asks_what_kind_of_node_it_has():
    """Directory.accept and File.accept dispatch; the caller does not branch."""
    root = Directory()
    root.add(File("a.txt", "12345"))

    assert DiskUsageVisitor().run(root).total_bytes == 5


def test_a_new_operation_needs_no_change_to_the_nodes():
    """The Visitor trade: operations are cheap, node types are expensive."""
    root = Directory()
    root.add(File("a.txt"))
    root.add(File("b.txt"))

    counter = FindVisitor(lambda node: node.name.endswith(".txt"))

    assert len(counter.run(root).matches) == 2


def test_the_tree_renders_the_root_as_a_single_slash(fs):
    assert fs.tree().splitlines()[0].startswith("/ ")


def test_the_tree_draws_the_last_child_with_a_corner(fs):
    lines = fs.tree("/src/app").splitlines()

    assert any(line.lstrip().startswith("└──") for line in lines)


def test_the_tree_can_hide_sizes(fs):
    assert "[" not in fs.tree(show_size=False)
