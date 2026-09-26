# Original Bug Squad reproduction with synthetic inputs.
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "upstream"
SOURCE = SOURCE / "src"
sys.path.insert(0, str(SOURCE))

import attrs

observed = []
@attrs.define
class Options:
    retries: int = attrs.field(kw_only=True, default=7)
    def __attrs_pre_init__(self, *, retries):
        observed.append(retries)

options = Options()
assert observed == [7]
assert options.retries == 7
