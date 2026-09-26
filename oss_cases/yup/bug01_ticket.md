# Concatenation forgets an object schema's dependency exclusions

An object schema with mutually dependent fields and an explicit excluded dependency edge can be created successfully. Concatenating another object schema then reports a cycle. The exclusion should remain effective after concatenation.

## Reproduction

1. Create two string fields whose conditional requiredness depends on each other.
2. Exclude one dependency edge when defining the object shape.
3. Concatenate an empty object schema onto that schema.
4. Check that construction and a simple validity check complete without a dependency-cycle exception.

## Local case

- Upstream report: [jquense/yup #1423](https://github.com/jquense/yup/issues/1423). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [f3056f2cbade92eaf0427848f43df97eae010555](https://github.com/jquense/yup/tree/f3056f2cbade92eaf0427848f43df97eae010555).
- Source root: `bug01/upstream/`; paths in `bug01_files.txt` are relative to this root.
- Primary affected source: `src/object.ts`, `src/util/sortFields.ts`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
node oss_cases/yup/run.cjs bug01
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
