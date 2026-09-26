# Original Bug Squad reproduction with synthetic inputs.
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "upstream"
SOURCE = SOURCE / "src"
sys.path.insert(0, str(SOURCE))

import attrs

@attrs.define
class Measurement:
    count = attrs.field(default=None, converter=attrs.converters.optional(attrs.converters.pipe(str, int)))

assert Measurement().count is None
assert Measurement("42").count == 42
