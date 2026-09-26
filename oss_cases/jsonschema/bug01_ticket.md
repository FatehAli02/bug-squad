# Inspecting a valid array position changes the error index

Looking up an error-free position in an ErrorTree changes which positions the tree reports as containing errors. Read-only inspection should leave membership and iteration unchanged.

## Reproduction

1. Validate an array containing a string and an integer against an integer-items schema.
2. Build an ErrorTree and confirm that only the first position contains an error.
3. Read the subtree for the second, valid position.
4. Check membership and iteration again; the second position should still be absent.

## Local case

- Upstream report: [python-jsonschema/jsonschema #1328](https://github.com/python-jsonschema/jsonschema/issues/1328). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [edf3dc38d29d275c277a85c00dd4d57f21db0de6](https://github.com/python-jsonschema/jsonschema/tree/edf3dc38d29d275c277a85c00dd4d57f21db0de6).
- Source root: `bug01/upstream/`; paths in `bug01_files.txt` are relative to this root.
- Primary affected source: `jsonschema/exceptions.py`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
python3 oss_cases/jsonschema/bug01/reproduce.py
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
