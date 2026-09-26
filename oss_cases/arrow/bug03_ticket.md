# A past timestamp is described as future when zero-valued units are included

Humanizing an earlier timestamp with several units can choose future wording when some units have a zero value. The relative direction should still describe the timestamp as being in the past.

## Reproduction

1. Create a timestamp and a comparison timestamp two hours later.
2. Humanize the first relative to the second with second, hour, and day units.
3. Inspect the relative wording.
4. Expect past-tense wording rather than a future prefix.

## Local case

- Upstream report: [arrow-py/arrow #996](https://github.com/arrow-py/arrow/issues/996). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [be57df5a7474dda3f6c16176ad181fa176039f2c](https://github.com/arrow-py/arrow/tree/be57df5a7474dda3f6c16176ad181fa176039f2c).
- Source root: `bug03/upstream/`; paths in `bug03_files.txt` are relative to this root.
- Primary affected source: `arrow/arrow.py`, `arrow/constants.py`, `arrow/locales.py`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
python3 oss_cases/arrow/bug03/reproduce.py
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
