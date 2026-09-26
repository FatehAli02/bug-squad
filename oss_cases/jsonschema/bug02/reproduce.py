# Original Bug Squad reproduction with synthetic inputs.
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "upstream"
sys.path.insert(0, str(SOURCE))

from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError

validator = Draft7Validator({"items": [{}], "additionalItems": False})
errors = list(validator.iter_errors([False, "extra", 42]))
assert len(errors) == 1
assert isinstance(errors[0], ValidationError)
assert "extra" in errors[0].message and "42" in errors[0].message
