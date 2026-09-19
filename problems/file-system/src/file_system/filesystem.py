"""A path-based front door onto the node tree.

Nothing here is new behaviour -- it is all `Directory.get` in a loop. But
callers think in paths, not in node references, and making them walk the tree
by hand would mean every one of them reimplementing the same loop with a
slightly different idea of what `..` means.
"""

from __future__ import annotations

from collections.abc import Callable

from .node import Directory, File, FileSystemNode
from .visitors import DiskUsageVisitor, FindVisitor, TreeRenderVisitor


class PathNotFound(Exception):
    """No node exists at that path."""


class NotADirectory(Exception):
    """A path component exists but is a file, so nothing can live inside it."""


class FileSystem:
    """The root of a tree, plus path resolution and the usual commands."""

    def __init__(self):
        self.root = Directory()

    # -- resolving --------------------------------------------------------

    @staticmethod
    def split(path: str) -> list[str]:
        """Split a path, resolving `.` and `..` as we go.

        Resolving here rather than after the walk means `..` never has to
        escape the root: popping an empty list is simply a no-op, which is what
        every real file system does for `/..`.
        """
        parts: list[str] = []
        for part in path.strip().split("/"):
            if part in {"", "."}:
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        return parts

    def resolve(self, path: str) -> FileSystemNode:
        node: FileSystemNode = self.root

        for index, part in enumerate(self.split(path)):
            if not isinstance(node, Directory):
                walked = "/" + "/".join(self.split(path)[:index])
                raise NotADirectory(f"{walked} is a file, so {path} cannot exist")

            child = node.get(part)
            if child is None:
                raise PathNotFound(f"No such file or directory: {path}")
            node = child

        return node

    def exists(self, path: str) -> bool:
        try:
            self.resolve(path)
        except (PathNotFound, NotADirectory):
            return False
        return True

    def _parent_of(self, path: str, create: bool = False) -> tuple[Directory, str]:
        parts = self.split(path)
        if not parts:
            raise ValueError("The root has no parent")

        node: FileSystemNode = self.root
        for part in parts[:-1]:
            if not isinstance(node, Directory):
                raise NotADirectory(f"{node.path} is a file, so {path} cannot exist")

            child = node.get(part)
            if child is None:
                if not create:
                    raise PathNotFound(f"No such directory: {node.path}/{part}")
                child = node.add(Directory(part))
            node = child

        if not isinstance(node, Directory):
            raise NotADirectory(f"{node.path} is a file, so {path} cannot exist")
        return node, parts[-1]

    # -- commands ---------------------------------------------------------

    def mkdir(self, path: str, parents: bool = False) -> Directory:
        parent, name = self._parent_of(path, create=parents)

        existing = parent.get(name)
        if existing is not None:
            if parents and isinstance(existing, Directory):
                # `mkdir -p` on something that already exists is a success,
                # which is the whole reason the flag exists.
                return existing
            raise FileExistsError(f"{path} already exists")

        return parent.add(Directory(name))

    def touch(self, path: str, content: str = "", parents: bool = False) -> File:
        parent, name = self._parent_of(path, create=parents)

        existing = parent.get(name)
        if isinstance(existing, File):
            return existing
        if existing is not None:
            raise FileExistsError(f"{path} is a directory")

        return parent.add(File(name, content))

    def write(self, path: str, content: str, parents: bool = True) -> File:
        file = self.touch(path, parents=parents)
        file.write(content)
        return file

    def read(self, path: str) -> str:
        node = self.resolve(path)
        if not isinstance(node, File):
            raise IsADirectoryError(f"{path} is a directory")
        return node.content

    def ls(self, path: str = "/") -> list[str]:
        node = self.resolve(path)
        if isinstance(node, File):
            return [node.name]
        return [f"{child.name}/" if child.is_directory else child.name for child in node]

    def rm(self, path: str, recursive: bool = False) -> FileSystemNode:
        node = self.resolve(path)
        if node is self.root:
            raise ValueError("Cannot remove the root")

        if isinstance(node, Directory) and len(node) and not recursive:
            raise ValueError(f"{path} is not empty; pass recursive=True to remove it anyway")

        return node.parent.remove(node.name)

    def move(self, source: str, destination: str) -> FileSystemNode:
        node = self.resolve(source)
        if node is self.root:
            raise ValueError("Cannot move the root")

        parent, name = self._parent_of(destination)

        # Detach only once the destination is known to be valid, so a failed
        # move does not leave the node orphaned.
        if name in parent:
            raise FileExistsError(f"{destination} already exists")

        node.parent.remove(node.name)
        node.name = name
        return parent.add(node)

    # -- traversals -------------------------------------------------------

    def du(self, path: str = "/") -> DiskUsageVisitor:
        return DiskUsageVisitor().run(self.resolve(path))

    def size(self, path: str = "/") -> int:
        return self.resolve(path).size

    def find(
        self,
        path: str = "/",
        *,
        name: str | None = None,
        extension: str | None = None,
        predicate: Callable[[FileSystemNode], bool] | None = None,
    ) -> list[str]:
        """Search by name, extension, or an arbitrary predicate."""
        if predicate is None:

            def predicate(node: FileSystemNode) -> bool:
                if name is not None and node.name != name:
                    return False
                if extension is not None:
                    return isinstance(node, File) and node.extension == extension.lower().lstrip(
                        "."
                    )
                return name is not None

        return FindVisitor(predicate).run(self.resolve(path)).paths

    def tree(self, path: str = "/", show_size: bool = True) -> str:
        return TreeRenderVisitor(show_size).run(self.resolve(path)).render()
