# Extending a legacy validator changes reference-sibling handling

An unchanged extension of the Draft 4 validator rejects data accepted by the original validator. A sibling constraint next to a reference should remain ignored under the parent draft's rules.

## Reproduction

1. Create a Draft 4 schema referencing a numeric definition and place a maximum constraint next to that reference.
2. Validate the number 9 with the standard validator.
3. Extend that validator without replacing any validation handlers.
4. Validate the same number with the derived validator and expect the same result.

## Local case

- Upstream report: [python-jsonschema/jsonschema #1125](https://github.com/python-jsonschema/jsonschema/issues/1125). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [52c2419625e875e7e7c8124bcbfae8cde92bbda3](https://github.com/python-jsonschema/jsonschema/tree/52c2419625e875e7e7c8124bcbfae8cde92bbda3).
- Source root: `bug03/upstream/`; paths in `bug03_files.txt` are relative to this root.
- Primary affected source: `jsonschema/validators.py`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
python3 oss_cases/jsonschema/bug03/reproduce.py
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
