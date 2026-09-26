# Reproducer tests for python-jsonschema/jsonschema bugs.
# Each test asserts the CORRECT behavior and therefore FAILS on the pre-fix
# snapshot.  After the upstream fix is applied the test passes.
#
# Each test runs reproduce.py in a fresh subprocess to prevent module-cache
# pollution between different buggy upstream snapshots.
#
# Run from the repository root:
#   pytest oss_cases/jsonschema/test_bugs.py -v
import subprocess
import sys
from pathlib import Path

REPRODUCE_ROOT = Path(__file__).resolve().parent


def _run_reproduce(bug: str) -> subprocess.CompletedProcess:
    script = REPRODUCE_ROOT / bug / "reproduce.py"
    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# bug01 — Inspecting a valid array position changes the error index
# python-jsonschema/jsonschema #1328
# Primary affected source: jsonschema/exceptions.py
# ---------------------------------------------------------------------------

def test_jsonschema_bug01_reading_valid_position_does_not_mutate_error_tree():
    """Accessing tree[valid_index] must not insert that index into the error set.

    Given:
        tree = ErrorTree(validator.iter_errors(["invalid", 12]))
        # only index 0 has a type error
    When:
        subtree = tree[1]   # read-only access to valid position
    Then:
        1 not in tree           (membership unchanged)
        list(tree) == [0]       (iteration unchanged)

    On the BUGGY snapshot ErrorTree.__getitem__ stores a new child node in
    self._contents unconditionally, so after tree[1] is called 1 in tree
    returns True.  The test FAILS on the buggy snapshot.
    """
    result = _run_reproduce("bug01")
    assert result.returncode == 0, (
        "reproduce.py exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# bug02 — Mixed-type excess array values interrupt validation error reporting
# python-jsonschema/jsonschema #1157
# Primary affected source: jsonschema/_validators.py
# ---------------------------------------------------------------------------

def test_jsonschema_bug02_mixed_type_additional_items_yields_validation_error():
    """iter_errors must yield a ValidationError for additional-items violations, not raise.

    Given:
        schema = {"items": [{}], "additionalItems": False}
        instance = [False, "extra", 42]   # mixed-type extra values
    Then:
        list(iter_errors(instance)) == [one ValidationError]
        error.message contains both 'extra' and '42'

    On the BUGGY snapshot the additionalItems validator sorts extra items to
    build the error message, which raises TypeError when item types are
    incompatible (bool, str, int in Python 3).  The test FAILS on the buggy
    snapshot.
    """
    result = _run_reproduce("bug02")
    assert result.returncode == 0, (
        "reproduce.py exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# bug03 — Extending a legacy validator changes reference-sibling handling
# python-jsonschema/jsonschema #1125
# Primary affected source: jsonschema/validators.py
# ---------------------------------------------------------------------------

def test_jsonschema_bug03_extended_validator_behaves_identically_to_base():
    """validators.extend(Draft4Validator) must not change $ref-sibling behaviour.

    Given:
        schema has a $ref plus a sibling maximum:3 keyword
        Draft4Validator(schema).is_valid(9) == True   # $ref ignores siblings in Draft4
    When:
        Derived = validators.extend(Draft4Validator)
    Then:
        Derived(schema).is_valid(9) == True   # unchanged extension same as base

    On the BUGGY snapshot extend() changes the internal validator registry
    lookup so that Derived enforces the sibling maximum keyword, making
    is_valid(9) return False.  The test FAILS on the buggy snapshot.
    """
    result = _run_reproduce("bug03")
    assert result.returncode == 0, (
        "reproduce.py exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )
