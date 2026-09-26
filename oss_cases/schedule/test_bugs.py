# Reproducer tests for dbader/schedule bugs.
# Each test asserts the CORRECT behavior and therefore FAILS on the pre-fix
# snapshot.  After the upstream fix is applied the test passes.
#
# Each test runs reproduce.py in a fresh subprocess to prevent module-cache
# pollution between different buggy upstream snapshots.
#
# Run from the repository root:
#   pytest oss_cases/schedule/test_bugs.py -v
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
# bug01 — A daily job finishing after midnight misses its next evening run
# dbader/schedule #304
# Primary affected source: schedule/__init__.py
# ---------------------------------------------------------------------------

def test_schedule_bug01_next_run_is_same_day_after_midnight_completion():
    """next_run must be scheduled for 21:30 on the day of completion, not the next.

    Given:
        Clock frozen at 2022-06-10 20:00
        job = every().day.at("21:30")
    When:
        Clock advances to 2022-06-11 02:00 and job.run() is called
    Then:
        job.next_run == datetime(2022, 6, 11, 21, 30)

    On the BUGGY snapshot _schedule_next_run advances by a full 24 h offset
    without checking whether the target time is still ahead on the current
    calendar day, so next_run lands on 2022-06-12 21:30 instead.  The test
    FAILS on the buggy snapshot.
    """
    result = _run_reproduce("bug01")
    assert result.returncode == 0, (
        "reproduce.py exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# bug02 — An hourly schedule loses the requested seconds component
# dbader/schedule #286
# Primary affected source: schedule/__init__.py
# ---------------------------------------------------------------------------

def test_schedule_bug02_hourly_at_preserves_seconds():
    """every().hour.at('MM:SS') must store both minutes and seconds in at_time.

    Given:
        job = every().hour.at("17:43")
    Then:
        job.at_time.minute == 17 and job.at_time.second == 43

    On the BUGGY snapshot the at() parser for hourly jobs discards the seconds
    field, so at_time.second == 0 instead of 43.  The test FAILS on the buggy
    snapshot.
    """
    result = _run_reproduce("bug02")
    assert result.returncode == 0, (
        "reproduce.py exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# bug03 — Formatting a job that receives itself as an argument recurses
# dbader/schedule #190
# Primary affected source: schedule/__init__.py
# ---------------------------------------------------------------------------

def test_schedule_bug03_repr_does_not_recurse_when_job_is_own_argument():
    """repr(job) must terminate in finite time when job is passed as its own argument.

    Given:
        job = every().minute
        job.do(lambda current_job: None, job)
    Then:
        repr(job) returns a short string without recursing

    On the BUGGY snapshot __repr__ calls repr() on each job argument; when the
    job itself is an argument this recurses infinitely, raising RecursionError.
    The test FAILS on the buggy snapshot.
    """
    result = _run_reproduce("bug03")
    assert result.returncode == 0, (
        "reproduce.py exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )
