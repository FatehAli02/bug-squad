# Czech and Slovak humanization fail when a selected unit is zero

Formatting a one-day difference with both minute and day units fails for the Czech and Slovak locales because the selected minutes component is zero. Both locales should return a usable string.

## Reproduction

1. Create a reference timestamp and another timestamp one day earlier.
2. Humanize the earlier timestamp with minute and day granularity.
3. Repeat with the cs and sk locales.
4. Expect nonempty strings from both calls.

## Local case

- Upstream report: [arrow-py/arrow #1078](https://github.com/arrow-py/arrow/issues/1078). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [a2ebb7e20b4897ee7b7bf4676a5ac3e6c0f27f47](https://github.com/arrow-py/arrow/tree/a2ebb7e20b4897ee7b7bf4676a5ac3e6c0f27f47).
- Source root: `bug02/upstream/`; paths in `bug02_files.txt` are relative to this root.
- Primary affected source: `arrow/constants.py`, `arrow/locales.py`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
python3 oss_cases/arrow/bug02/reproduce.py
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
