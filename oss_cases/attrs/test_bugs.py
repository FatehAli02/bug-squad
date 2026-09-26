# Reproducer tests for python-attrs/attrs bugs.
# Each test asserts the CORRECT behavior and therefore FAILS on the pre-fix
# snapshot.  After the upstream fix is applied the test passes.
#
# Each test runs reproduce.py in a fresh subprocess to prevent module-cache
# pollution between different buggy upstream snapshots.
#
# Run from the repository root:
#   pytest oss_cases/attrs/test_bugs.py -v
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
# bug01 — A nullable conversion pipeline rejects supplied values
# python-attrs/attrs #1348
# Primary affected source: src/attr/converters.py
# ---------------------------------------------------------------------------

def test_attrs_bug01_optional_pipe_converter_accepts_value():
    """optional(pipe(str, int)) must convert a supplied value to int without error.

    Given:
        count = field(default=None,
                      converter=optional(pipe(str, int)))
    When:
        Measurement("42") is constructed
    Then:
        instance.count == 42

    On the BUGGY snapshot the optional converter calls the inner pipeline with
    extra ``instance`` and ``field`` positional arguments that the pipeline
    lambda does not accept, raising TypeError.  The test FAILS on the buggy
    snapshot.
    """
    result = _run_reproduce("bug01")
    assert result.returncode == 0, (
        "reproduce.py exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# bug02 — Reassigning a field with chained converters raises an internal error
# python-attrs/attrs #1327
# Primary affected source: src/attr/setters.py
# ---------------------------------------------------------------------------

def test_attrs_bug02_chained_converter_runs_on_reassignment():
    """Assigning a new value to a list-converter field must run all converters.

    Given:
        value = field(converter=[str, int])
    When:
        counter.value = "19"   (after construction)
    Then:
        counter.value == 19   (int, not str)

    On the BUGGY snapshot the on_setattr hook stores a Converter object that
    lacks __call__, so assignment raises AttributeError.  The test FAILS on the
    buggy snapshot.
    """
    result = _run_reproduce("bug02")
    assert result.returncode == 0, (
        "reproduce.py exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# bug03 — A defaulted keyword-only field prevents class creation with a
#          pre-init hook
# python-attrs/attrs #1284
# Primary affected source: src/attr/_make.py
# ---------------------------------------------------------------------------

def test_attrs_bug03_kw_only_default_with_pre_init_creates_class():
    """@attrs.define must succeed when kw_only+default combines with __attrs_pre_init__.

    Given:
        retries: int = field(kw_only=True, default=7)
        def __attrs_pre_init__(self, *, retries): ...
    When:
        Options() is constructed (no arguments)
    Then:
        pre_init received retries=7 and options.retries == 7

    On the BUGGY snapshot _make_init generates an invalid ``__init__``
    signature, causing a SyntaxError at class-creation time.  The test FAILS
    on the buggy snapshot.
    """
    result = _run_reproduce("bug03")
    assert result.returncode == 0, (
        "reproduce.py exited non-zero — bug is present:\n"
        f"stderr: {result.stderr}"
    )
