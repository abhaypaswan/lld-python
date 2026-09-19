"""A fixed-size cache whose eviction policy is a swappable strategy."""

from .cache import Cache
from .policies import FIFOPolicy, LFUPolicy, LRUPolicy

__all__ = ["Cache", "LRUPolicy", "LFUPolicy", "FIFOPolicy"]
