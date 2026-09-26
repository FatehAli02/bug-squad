# An empty humanization unit selection raises the wrong exception

Passing no units to humanize triggers an internal failure instead of a clear input-validation exception. An empty unit selection should be rejected with ValueError.

## Reproduction

1. Create two Arrow timestamps separated by two hours.
2. Call humanize with an empty granularity list.
3. Check that the call rejects the input with ValueError.

## Local case

- Upstream report: [arrow-py/arrow #1015](https://github.com/arrow-py/arrow/issues/1015). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [f7a3aa3225eb646fec9156e8e39dc33750f2a227](https://github.com/arrow-py/arrow/tree/f7a3aa3225eb646fec9156e8e39dc33750f2a227).
- Source root: `bug01/upstream/`; paths in `bug01_files.txt` are relative to this root.
- Primary affected source: `arrow/arrow.py`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
python3 oss_cases/arrow/bug01/reproduce.py
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
