# Mixed-type excess array values interrupt validation error reporting

When an array has forbidden extra entries of different Python types, validation can raise a Python exception while building the error message. It should return an ordinary validation error describing the extra entries.

## Reproduction

1. Create a Draft 7 schema with one permitted array position and no additional items.
2. Validate an array whose extra positions contain a string and an integer.
3. Collect the validation errors.
4. Expect one ValidationError rather than a type-comparison exception.

## Local case

- Upstream report: [python-jsonschema/jsonschema #1157](https://github.com/python-jsonschema/jsonschema/issues/1157). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [d9be1a49fa49dc5fdd3b20344ab57dad24c6e82d](https://github.com/python-jsonschema/jsonschema/tree/d9be1a49fa49dc5fdd3b20344ab57dad24c6e82d).
- Source root: `bug02/upstream/`; paths in `bug02_files.txt` are relative to this root.
- Primary affected source: `jsonschema/_keywords.py`, `jsonschema/_utils.py`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
python3 oss_cases/jsonschema/bug02/reproduce.py
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
