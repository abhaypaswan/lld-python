"""Put this problem's `src` on sys.path, so its tests run from anywhere.

pytest loads the nearest conftest.py before importing the test modules beneath
it, which is what makes this work whether you run:

    pytest                                  # from this directory
    pytest problems/movie-ticket-booking          # from the repo root
    pytest tests/test_movie_ticket_booking.py  # a single file

It also means the directory is genuinely self-contained: copy it out of the
repository and the tests still run, with no repo-level setup to remember.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
