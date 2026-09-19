"""Visitor: operations that walk the tree without living on it.

Disk usage, search and rendering are all the same traversal with different
bookkeeping. Put each on the nodes and every new operation edits both `File`
and `Directory`; the node classes slowly become a junk drawer of unrelated
methods.

As visitors, a new operation is one new class and nothing existing changes.
The trade is the one the pattern always makes: adding an *operation* is now
cheap, adding a *node type* is expensive, because every visitor grows a method.
For a file system that is the right way round -- there are two node types and
there will always be two, while operations keep arriving.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from .node import Directory, File, FileSystemNode


class NodeVisitor(ABC):
    """One operation over the tree."""

    @abstractmethod
    def visit_file(self, file: File) -> None: ...

    @abstractmethod
    def visit_directory(self, directory: Directory) -> None: ...

    def run(self, node: FileSystemNode) -> NodeVisitor:
        """Visit `node`, and return self so results can be read off inline."""
        node.accept(self)
        return self


class DiskUsageVisitor(NodeVisitor):
    """Totals bytes, and counts what it saw on the way."""

    def __init__(self):
        self.total_bytes = 0
        self.file_count = 0
        self.directory_count = 0
        self.by_extension: dict[str, int] = {}

    def visit_file(self, file: File) -> None:
        self.total_bytes += file.size
        self.file_count += 1
        extension = file.extension or "(none)"
        self.by_extension[extension] = self.by_extension.get(extension, 0) + file.size

    def visit_directory(self, directory: Directory) -> None:
        self.directory_count += 1
        for child in directory:
            child.accept(self)

    def summary(self) -> str:
        return (
            f"{self.total_bytes} bytes across {self.file_count} files "
            f"in {self.directory_count} directories"
        )


class FindVisitor(NodeVisitor):
    """Collects every node matching a predicate."""

    def __init__(self, predicate: Callable[[FileSystemNode], bool]):
        self.predicate = predicate
        self.matches: list[FileSystemNode] = []

    def visit_file(self, file: File) -> None:
        self._check(file)

    def visit_directory(self, directory: Directory) -> None:
        self._check(directory)
        for child in directory:
            child.accept(self)

    def _check(self, node: FileSystemNode) -> None:
        if self.predicate(node):
            self.matches.append(node)

    @property
    def paths(self) -> list[str]:
        return [node.path for node in self.matches]


class TreeRenderVisitor(NodeVisitor):
    """Draws the tree the way `tree(1)` does."""

    def __init__(self, show_size: bool = True):
        self.show_size = show_size
        self.lines: list[str] = []
        self._prefixes: list[str] = []

    def visit_file(self, file: File) -> None:
        self.lines.append(self._line(file.name, file.size))

    def visit_directory(self, directory: Directory) -> None:
        # The root already reads as "/", so it must not gain a second slash.
        label = f"{directory.name}/" if directory.name else "/"
        self.lines.append(self._line(label, directory.size))

        children = directory.children
        for index, child in enumerate(children):
            last = index == len(children) - 1
            self._prefixes.append("└── " if last else "├── ")
            child.accept(self)
            self._prefixes.pop()

    def _line(self, label: str, size: int) -> str:
        # Everything above the current node becomes a spacer: a pipe where that
        # branch continues, blank where it was the last child.
        indent = "".join(
            ("    " if prefix.startswith("└") else "│   ") for prefix in self._prefixes[:-1]
        )
        connector = self._prefixes[-1] if self._prefixes else ""
        suffix = f"  [{size}]" if self.show_size else ""
        return f"{indent}{connector}{label}{suffix}"

    def render(self) -> str:
        return "\n".join(self.lines)
