# Reproducer tests for arrow-py/arrow bugs.
# Each test asserts the CORRECT behavior and therefore FAILS on the pre-fix
# snapshot.  After the upstream fix is applied the test passes.
#
# Each test runs reproduce.py in a fresh subprocess to prevent module-cache
# pollution between different buggy upstream snapshots.
#
# Run from the repository root:
#   pytest oss_cases/arrow/test_bugs.py -v
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
# bug01 — An empty humanization unit selection raises the wrong exception
# arrow-py/arrow #1015
# Primary affected source: arrow/arrow.py
# ---------------------------------------------------------------------------

def test_arrow_bug01_empty_granularity_raises_value_error():
    """humanize(granularity=[]) must raise ValueError to signal invalid input.

    Given:
        start = Arrow(2022, 4, 5, 10, 0)
    When:
        start.humanize(start.shift(hours=2), granularity=[])
    Then:
        ValueError is raised (not IndexError or any other internal exception)

    On the BUGGY snapshot humanize processes an empty granularity list without
    validation, resulting in an IndexError from inside the function rather than
    a user-facing ValueError.  The test FAILS on the buggy snapshot.
    """
    result = _run_reproduce("bug01")
    assert result.returncode == 0, (
        "reproduce.py exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# bug02 — Czech and Slovak humanization fail when a selected unit is zero
# arrow-py/arrow #1078
# Primary affected source: arrow/locales.py
# ---------------------------------------------------------------------------

def test_arrow_bug02_cs_sk_humanize_with_zero_minute_unit():
    """humanize(granularity=['minute','day']) must succeed for cs and sk locales.

    Given:
        reference = Arrow(2022, 4, 5, 10, 0)
        earlier   = reference.shift(days=-1)
        # minutes component is 0 in the multi-unit breakdown
    When:
        earlier.humanize(reference, locale=locale, granularity=['minute', 'day'])
        for locale in ('cs', 'sk')
    Then:
        A non-empty string is returned for both locales

    On the BUGGY snapshot the Czech/Slovak plural helpers do not handle zero
    as a valid value, raising KeyError when the minutes unit is 0.  The test
    FAILS on the buggy snapshot.
    """
    result = _run_reproduce("bug02")
    assert result.returncode == 0, (
        "reproduce.py exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# bug03 — A past timestamp is described as future when zero-valued units are
#          included in the granularity
# arrow-py/arrow #996
# Primary affected source: arrow/arrow.py
# ---------------------------------------------------------------------------

def test_arrow_bug03_past_timestamp_humanizes_as_past_tense():
    """humanize of a past timestamp must end with 'ago', not use future tense.

    Given:
        earlier = Arrow(2022, 4, 5, 10, 0)
        later   = earlier.shift(hours=2)
    When:
        earlier.humanize(later, granularity=['second', 'hour', 'day'])
        # earlier is in the PAST relative to later
    Then:
        result.endswith('ago')

    On the BUGGY snapshot the sign-calculation sums all selected units including
    zero-valued ones, which can flip the sign for a genuinely-past timestamp so
    it is described as "in X seconds" (future tense).  The test FAILS on the
    buggy snapshot.
    """
    result = _run_reproduce("bug03")
    assert result.returncode == 0, (
        "reproduce.py exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )
