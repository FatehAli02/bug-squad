# A daily job finishing after midnight misses its next evening run

A daily job that finishes on the following calendar day can be scheduled one day too late. Completing after midnight should still allow the next run at the configured time later that same day.

## Reproduction

1. Freeze the clock at 20:00 and schedule a daily job for 21:30.
2. Simulate completion at 02:00 on the following day.
3. Ask the job to calculate its next run after completion.
4. Expect 21:30 on the completion day, rather than the day after that.

## Local case

- Upstream report: [dbader/schedule #304](https://github.com/dbader/schedule/issues/304). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [705f3730e40fd1a4451dedcf28de510aa5c86212](https://github.com/dbader/schedule/tree/705f3730e40fd1a4451dedcf28de510aa5c86212).
- Source root: `bug01/upstream/`; paths in `bug01_files.txt` are relative to this root.
- Primary affected source: `schedule/__init__.py`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
python3 oss_cases/schedule/bug01/reproduce.py
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
