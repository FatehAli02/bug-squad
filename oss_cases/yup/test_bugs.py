# Reproducer tests for jquense/yup bugs.
# Each test asserts the CORRECT JavaScript behavior and therefore FAILS on the
# pre-fix snapshot.  After the upstream fix is applied the test passes.
#
# The yup source is TypeScript/JavaScript; tests are run via the existing
# run.cjs runner (which uses esbuild to bundle and node to execute).
#
# Run from the repository root:
#   pytest oss_cases/yup/test_bugs.py -v
#
# Prerequisites: npm ci --prefix oss_cases/yup --ignore-scripts --no-audit --no-fund
import subprocess
import shutil
from pathlib import Path


YUP_ROOT = Path(__file__).resolve().parent


def _run_yup_bug(bug: str) -> subprocess.CompletedProcess:
    node = shutil.which("node")
    assert node is not None, "node not found on PATH"
    runner = YUP_ROOT / "run.cjs"
    return subprocess.run(
        [node, str(runner), bug],
        capture_output=True,
        text=True,
        cwd=str(YUP_ROOT.parent.parent),  # repo root
    )


# ---------------------------------------------------------------------------
# bug01 — Concatenation forgets an object schema's dependency exclusions
# jquense/yup #1423
# Primary affected source: src/object.ts, src/util/sortFields.ts
# ---------------------------------------------------------------------------

def test_yup_bug01_concat_preserves_exclusion_pairs():
    """schema.concat(object()) must retain mutual-exclusion pairs from the base schema.

    Given:
        schema = object().shape({
            first:  string().when('second', { is: undefined, then: required() }),
            second: string().when('first',  { is: undefined, then: required() }),
        }, [['first', 'second']])   # exclusion pair prevents cycle detection
    When:
        combined = schema.concat(object())
    Then:
        combined.isValidSync({ first: 'present' }) === true

    On the BUGGY snapshot concat() does not copy the dependency exclusion list
    to the merged schema, so sortFields() sees an unresolvable cycle and throws
    Error("Cyclic dependency").  The test FAILS on the buggy snapshot.
    """
    result = _run_yup_bug("bug01")
    assert result.returncode == 0, (
        "run.cjs bug01 exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# bug02 — Ensuring an array discards a scalar input
# jquense/yup #343
# Primary affected source: src/array.js
# ---------------------------------------------------------------------------

def test_yup_bug02_ensure_wraps_scalar_in_array():
    """array().ensure().cast(23) must return [23], not an empty array.

    Given:
        schema = array().ensure()
    When:
        schema.cast(23)
    Then:
        result deepEquals [23]

    On the BUGGY snapshot ensure() calls the base cast which converts a
    non-array to an empty array [] instead of wrapping it, so 23 is discarded.
    The test FAILS on the buggy snapshot.
    """
    result = _run_yup_bug("bug02")
    assert result.returncode == 0, (
        "run.cjs bug02 exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# bug03 — Combining schemas removes an existing label and metadata
# jquense/yup #1160
# Primary affected source: src/schema.ts
# ---------------------------------------------------------------------------

def test_yup_bug03_concat_preserves_label_and_meta():
    """mixed().label('X').meta({...}).concat(mixed()) must preserve label and meta.

    Given:
        base = mixed().label('Quantity').meta({ section: 'inventory' })
    When:
        combined = base.concat(mixed())
    Then:
        combined.describe().label  === 'Quantity'
        combined.describe().meta   deepEquals { section: 'inventory' }

    On the BUGGY snapshot concat() overwrites _typeError and re-initialises
    label/meta from the incoming (empty) schema, clearing them to undefined.
    The test FAILS on the buggy snapshot.
    """
    result = _run_yup_bug("bug03")
    assert result.returncode == 0, (
        "run.cjs bug03 exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )
