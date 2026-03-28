from __future__ import annotations

import sys

from scrape_bible_to_db import *  # noqa: F401,F403
from scrape_bible_to_db import run


if __name__ == "__main__":
    sys.exit(run())
