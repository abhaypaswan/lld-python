from .fifo import FIFOPolicy
from .lfu import LFUPolicy
from .lru import LRUPolicy
from .policy import EvictionPolicy

POLICIES: dict[str, type[EvictionPolicy]] = {
    LRUPolicy.name: LRUPolicy,
    LFUPolicy.name: LFUPolicy,
    FIFOPolicy.name: FIFOPolicy,
}


def get_policy(name: str = "lru") -> EvictionPolicy:
    try:
        return POLICIES[name]()
    except KeyError:
        known = ", ".join(sorted(POLICIES))
        raise ValueError(f"{name!r} is not an eviction policy. Try one of: {known}") from None


__all__ = ["EvictionPolicy", "LRUPolicy", "LFUPolicy", "FIFOPolicy", "POLICIES", "get_policy"]
