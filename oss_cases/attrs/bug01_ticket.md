# A nullable conversion pipeline rejects supplied values

A field accepts its empty default but fails during initialization when a value must pass through a pipeline wrapped in the optional converter. Supplying a numeric string should produce an integer without an internal calling error.

## Reproduction

1. Define an attrs class with a field that defaults to None.
2. Use optional(pipe(str, int)) as that field's converter.
3. Construct one instance without an argument and another with the string "42".
4. Check that the second instance stores the integer 42.

## Local case

- Upstream report: [python-attrs/attrs #1348](https://github.com/python-attrs/attrs/issues/1348). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [ee0f19b696c60064c58cdc08b3265aef56d49ff8](https://github.com/python-attrs/attrs/tree/ee0f19b696c60064c58cdc08b3265aef56d49ff8).
- Source root: `bug01/upstream/`; paths in `bug01_files.txt` are relative to this root.
- Primary affected source: `src/attr/converters.py`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
python3 oss_cases/attrs/bug01/reproduce.py
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
