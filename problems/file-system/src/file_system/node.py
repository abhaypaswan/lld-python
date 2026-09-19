"""Composite: a directory is a node, and so is a file.

The whole point of the pattern is that a caller holding a `FileSystemNode`
never has to ask which one it has. `size` works on both. `path` works on both.
Code that walks the tree does not branch on type.

The alternative -- a Directory holding `files: list[File]` and
`subdirectories: list[Directory]` -- looks reasonable and then makes every
traversal written twice, once per list, forever.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator


class FileSystemNode(ABC):
    """Anything that can sit in a directory."""

    #: The root directory is the one node allowed an empty name, so that its
    #: path is "/" rather than "//something".
    allows_empty_name = False

    def __init__(self, name: str):
        if name or not self.allows_empty_name:
            validate_name(name)
        self.name = name
        #: Set by Directory.add. A node with no parent is a root.
        self.parent: Directory | None = None

    @property
    @abstractmethod
    def size(self) -> int:
        """Bytes. A file's content length; a directory's total, recursively."""

    @property
    @abstractmethod
    def is_directory(self) -> bool:
        """Kept so callers that genuinely must distinguish can, explicitly.

        Everything else on this class works without asking, which is the point.
        """

    @abstractmethod
    def accept(self, visitor) -> None:
        """Visitor: let an operation walk the tree without living on the tree.

        Search, disk usage and rendering are all traversals. Putting each one
        on the nodes means every new operation edits both File and Directory.
        """

    @property
    def path(self) -> str:
        """Absolute path, built by walking up to the root."""
        if self.parent is None:
            return "/" if self.name == "" else f"/{self.name}"

        parent_path = self.parent.path
        return f"{parent_path}{self.name}" if parent_path == "/" else f"{parent_path}/{self.name}"

    @property
    def depth(self) -> int:
        return 0 if self.parent is None else self.parent.depth + 1

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r})"


class File(FileSystemNode):
    """A leaf. Holds content and nothing else."""

    def __init__(self, name: str, content: str = ""):
        super().__init__(name)
        self.content = content

    @property
    def size(self) -> int:
        return len(self.content.encode("utf-8"))

    @property
    def is_directory(self) -> bool:
        return False

    @property
    def extension(self) -> str:
        _, dot, suffix = self.name.rpartition(".")
        return suffix.lower() if dot and _ else ""

    def write(self, content: str) -> int:
        self.content = content
        return self.size

    def append(self, content: str) -> int:
        self.content += content
        return self.size

    def accept(self, visitor) -> None:
        visitor.visit_file(self)


class Directory(FileSystemNode):
    """A composite. Holds other nodes, files and directories alike."""

    allows_empty_name = True

    def __init__(self, name: str = ""):
        super().__init__(name)
        self._children: dict[str, FileSystemNode] = {}

    # -- the composite operations -----------------------------------------

    @property
    def size(self) -> int:
        """Recursive, and deliberately not cached.

        A cached size has to be invalidated up the whole ancestor chain on
        every write, and the one path that forgets leaves a directory
        permanently reporting the wrong number.
        """
        return sum(child.size for child in self._children.values())

    @property
    def is_directory(self) -> bool:
        return True

    def accept(self, visitor) -> None:
        visitor.visit_directory(self)

    # -- children ---------------------------------------------------------

    def add(self, node: FileSystemNode) -> FileSystemNode:
        if node.name in self._children:
            raise FileExistsError(f"{self.path} already contains {node.name!r}")
        if node is self:
            raise ValueError("A directory cannot contain itself")
        if isinstance(node, Directory) and self._is_inside(node):
            # Without this, adding an ancestor to its own descendant creates a
            # cycle, and the next recursive size() call never returns.
            raise ValueError(f"Cannot add {node.path} into its own descendant {self.path}")

        node.parent = self
        self._children[node.name] = node
        return node

    def remove(self, name: str) -> FileSystemNode:
        node = self._children.pop(name, None)
        if node is None:
            raise FileNotFoundError(f"{self.path} contains no {name!r}")

        node.parent = None
        return node

    def get(self, name: str) -> FileSystemNode | None:
        return self._children.get(name)

    def _is_inside(self, ancestor: Directory) -> bool:
        node: FileSystemNode | None = self
        while node is not None:
            if node is ancestor:
                return True
            node = node.parent
        return False

    @property
    def children(self) -> list[FileSystemNode]:
        """Directories first, then files, each alphabetically. Like `ls`."""
        return sorted(self._children.values(), key=lambda n: (not n.is_directory, n.name.lower()))

    def __len__(self) -> int:
        return len(self._children)

    def __contains__(self, name: str) -> bool:
        return name in self._children

    # -- iteration --------------------------------------------------------

    def __iter__(self) -> Iterator[FileSystemNode]:
        """Direct children only, in `ls` order."""
        return iter(self.children)

    def walk(self) -> Iterator[FileSystemNode]:
        """Every node beneath this one, depth first.

        A generator rather than a list: a deep tree should not have to be
        materialised in full just to find the first match.
        """
        for child in self.children:
            yield child
            if isinstance(child, Directory):
                yield from child.walk()

    def files(self) -> Iterator[File]:
        return (node for node in self.walk() if isinstance(node, File))


def validate_name(name: str) -> None:
    if not name or not name.strip():
        raise ValueError("A name cannot be empty")
    if "/" in name:
        raise ValueError(f"{name!r} cannot contain '/'")
    if name in {".", ".."}:
        raise ValueError(f"{name!r} is reserved")
