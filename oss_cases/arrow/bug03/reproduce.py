# Original Bug Squad reproduction with synthetic inputs.
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "upstream"
sys.path.insert(0, str(SOURCE))

import arrow

earlier = arrow.Arrow(2022, 4, 5, 10, 0)
rendered = earlier.humanize(earlier.shift(hours=2), granularity=['second', 'hour', 'day'])
assert rendered.endswith('ago'), rendered
