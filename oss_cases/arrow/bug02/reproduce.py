# Original Bug Squad reproduction with synthetic inputs.
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "upstream"
sys.path.insert(0, str(SOURCE))

import arrow

reference = arrow.Arrow(2022, 4, 5, 10, 0)
earlier = reference.shift(days=-1)
for locale in ('cs', 'sk'):
    rendered = earlier.humanize(reference, locale=locale, granularity=['minute', 'day'])
    assert isinstance(rendered, str) and rendered
