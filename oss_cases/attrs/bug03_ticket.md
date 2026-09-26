# A defaulted keyword-only field prevents class creation with a pre-init hook

Combining a keyword-only field default with a pre-initialization hook that receives that field causes class decoration to fail. The class should be constructible and the hook should receive the default value.

## Reproduction

1. Declare an attrs class with a keyword-only field defaulting to 7.
2. Add a pre-initialization method accepting that field as a keyword argument.
3. Instantiate the class without explicitly providing the field.
4. Check that the hook observed 7 and the instance also stores 7.

## Local case

- Upstream report: [python-attrs/attrs #1284](https://github.com/python-attrs/attrs/issues/1284). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [689a0e64012d1e576ebd99e786a254bc537582c6](https://github.com/python-attrs/attrs/tree/689a0e64012d1e576ebd99e786a254bc537582c6).
- Source root: `bug03/upstream/`; paths in `bug03_files.txt` are relative to this root.
- Primary affected source: `src/attr/_make.py`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
python3 oss_cases/attrs/bug03/reproduce.py
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
