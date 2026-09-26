# Original Bug Squad reproduction with synthetic inputs.
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "upstream"
sys.path.insert(0, str(SOURCE))

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ErrorTree

validator = Draft202012Validator({"type": "array", "items": {"type": "integer"}})
tree = ErrorTree(validator.iter_errors(["invalid", 12]))
assert list(tree) == [0]
assert 1 not in tree
subtree = tree[1]
assert subtree.total_errors == 0
assert 1 not in tree, "Reading a valid position changed error membership"
assert list(tree) == [0]
