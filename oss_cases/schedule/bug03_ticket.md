# Formatting a job that receives itself as an argument recurses

A scheduled callback may need its own Job object as an argument. Producing a representation of that job should terminate instead of recursing through its argument list indefinitely.

## Reproduction

1. Create a pending job.
2. Register a callback that receives that same job as a positional argument.
3. Request the job's representation.
4. Expect a finite string without a recursion exception.

## Local case

- Upstream report: [dbader/schedule #190](https://github.com/dbader/schedule/issues/190). This ticket and its reproduction were independently written; no issue prose or diagnostic logs were copied.
- Source snapshot: [3108fc3194c2f3071d6e41adfd21577fc62c52fc](https://github.com/dbader/schedule/tree/3108fc3194c2f3071d6e41adfd21577fc62c52fc).
- Source root: `bug03/upstream/`; paths in `bug03_files.txt` are relative to this root.
- Primary affected source: `schedule/__init__.py`.
- Follow [the dependency setup](../README.md), then run from the Bug Squad repository root:

```sh
python3 oss_cases/schedule/bug03/reproduce.py
```

The reproduction asserts the expected behavior and therefore exits unsuccessfully on this intentionally buggy snapshot. See `../README.md` for the distinction between a reproduced bug and a missing dependency.
