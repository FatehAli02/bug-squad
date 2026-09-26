# Ensuring an array discards a scalar input

Casting a scalar through an array schema with ensure enabled drops the supplied value. The scalar should become the only element of the resulting array.

## Reproduction

1. Create an array schema with ensure enabled.
2. Cast the number 23 through it.
3. Check that the result contains exactly that number.

## Local case

- Upstream report: [jquense/yup #343](https://github.com/jquense/yup/issues/343). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [3d90d6f49da00883b33d34240f24069d695ec1e8](https://github.com/jquense/yup/tree/3d90d6f49da00883b33d34240f24069d695ec1e8).
- Source root: `bug02/upstream/`; paths in `bug02_files.txt` are relative to this root.
- Primary affected source: `src/array.js`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
node oss_cases/yup/run.cjs bug02
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
