# Original Bug Squad reproduction with synthetic inputs.
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "upstream"
sys.path.insert(0, str(SOURCE))

import arrow

start = arrow.Arrow(2022, 4, 5, 10, 0)
try:
    start.humanize(start.shift(hours=2), granularity=[])
except ValueError:
    pass
else:
    raise AssertionError("An empty unit selection was accepted")
