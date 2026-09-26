# Combining schemas removes an existing label and metadata

Concatenating a plain mixed schema onto one with a label and metadata clears those settings. Settings that the second schema never supplied should remain available on the combined schema.

## Reproduction

1. Create a mixed schema with a display label and a metadata key.
2. Concatenate a fresh mixed schema without either setting.
3. Inspect the resulting schema description.
4. Expect the original display label and metadata to remain.

## Local case

- Upstream report: [jquense/yup #1160](https://github.com/jquense/yup/issues/1160). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [e785e1a4ddf1b7fb2d1ef48cb258d8e21a775446](https://github.com/jquense/yup/tree/e785e1a4ddf1b7fb2d1ef48cb258d8e21a775446).
- Source root: `bug03/upstream/`; paths in `bug03_files.txt` are relative to this root.
- Primary affected source: `src/schema.ts`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
node oss_cases/yup/run.cjs bug03
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
