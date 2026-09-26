# Original Bug Squad reproduction with synthetic inputs.
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "upstream"
SOURCE = SOURCE / "src"
sys.path.insert(0, str(SOURCE))

import attrs

@attrs.define
class Counter:
    value = attrs.field(converter=[str, int])

counter = Counter("8")
counter.value = "19"
assert counter.value == 19
