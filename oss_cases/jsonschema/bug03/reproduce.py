# Original Bug Squad reproduction with synthetic inputs.
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "upstream"
sys.path.insert(0, str(SOURCE))

from jsonschema import Draft4Validator, validators

schema = {"definitions": {"quantity": {"type": "number"}}, "$ref": "#/definitions/quantity", "maximum": 3}
assert Draft4Validator(schema).is_valid(9)
Derived = validators.extend(Draft4Validator)
assert Derived(schema).is_valid(9), "An unchanged extension rejected previously valid data"
