# An hourly schedule loses the requested seconds component

A two-part time supplied to an hourly job is interpreted with the wrong units. The two components should specify the minute and second within each hour.

## Reproduction

1. Create an hourly job using at("17:43").
2. Inspect the time assigned to the job.
3. Expect minute 17 and second 43.

## Local case

- Upstream report: [dbader/schedule #286](https://github.com/dbader/schedule/issues/286). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [b3e75d28134c51bae3a37793b8b5ca52353c9753](https://github.com/dbader/schedule/tree/b3e75d28134c51bae3a37793b8b5ca52353c9753).
- Source root: `bug02/upstream/`; paths in `bug02_files.txt` are relative to this root.
- Primary affected source: `schedule/__init__.py`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
python3 oss_cases/schedule/bug02/reproduce.py
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
