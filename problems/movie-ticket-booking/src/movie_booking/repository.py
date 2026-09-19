"""Repository, and a Proxy in front of it.

`ShowRepository` is an interface, not a dict, so the service never learns where
shows come from. Swapping the in-memory store for a database is a new
implementation and no change to anything that reads shows.

`CachingShowRepository` is a genuine Proxy: it implements the same interface,
holds the real repository, and controls access to it -- here by remembering
answers. A caller cannot tell the difference, which is the whole test of
whether something is a proxy or just a helper.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Show


class ShowRepository(ABC):
    """Where shows are looked up."""

    @abstractmethod
    def add(self, show: Show) -> Show: ...

    @abstractmethod
    def get(self, show_id: str) -> Show | None: ...

    @abstractmethod
    def for_movie(self, movie_id: str) -> list[Show]: ...

    @abstractmethod
    def in_city(self, city: str) -> list[Show]: ...

    @abstractmethod
    def all(self) -> list[Show]: ...


class InMemoryShowRepository(ShowRepository):
    """The real thing, for now. A database implementation slots in beside it."""

    def __init__(self):
        self._shows: dict[str, Show] = {}
        #: Counted so a test can prove the proxy in front actually avoids work.
        self.query_count = 0

    def add(self, show: Show) -> Show:
        if show.show_id in self._shows:
            raise ValueError(f"Show {show.show_id} already exists")
        self._shows[show.show_id] = show
        return show

    def get(self, show_id: str) -> Show | None:
        self.query_count += 1
        return self._shows.get(show_id)

    def for_movie(self, movie_id: str) -> list[Show]:
        self.query_count += 1
        return [s for s in self._shows.values() if s.movie.movie_id == movie_id]

    def in_city(self, city: str) -> list[Show]:
        self.query_count += 1
        wanted = city.strip().lower()
        return [s for s in self._shows.values() if s.theatre.city.lower() == wanted]

    def all(self) -> list[Show]:
        self.query_count += 1
        return list(self._shows.values())


class CachingShowRepository(ShowRepository):
    """Proxy: same interface, remembers answers, invalidates on write.

    Listings are read constantly and change rarely, which is exactly when a
    caching proxy is worth it. The important half is `add` clearing the cache --
    a proxy that caches reads and forgets to invalidate on write is worse than
    no proxy, because it is confidently wrong.
    """

    def __init__(self, inner: ShowRepository):
        self.inner = inner
        self._cache: dict[tuple[str, str], object] = {}
        self.hits = 0
        self.misses = 0

    def _cached(self, key: tuple[str, str], produce):
        if key in self._cache:
            self.hits += 1
            return self._cache[key]

        self.misses += 1
        value = produce()
        self._cache[key] = value
        return value

    def add(self, show: Show) -> Show:
        result = self.inner.add(show)
        self.invalidate()
        return result

    def get(self, show_id: str) -> Show | None:
        return self._cached(("get", show_id), lambda: self.inner.get(show_id))

    def for_movie(self, movie_id: str) -> list[Show]:
        return self._cached(("movie", movie_id), lambda: self.inner.for_movie(movie_id))

    def in_city(self, city: str) -> list[Show]:
        key = ("city", city.strip().lower())
        return self._cached(key, lambda: self.inner.in_city(city))

    def all(self) -> list[Show]:
        return self._cached(("all", ""), self.inner.all)

    def invalidate(self) -> None:
        self._cache.clear()

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0
