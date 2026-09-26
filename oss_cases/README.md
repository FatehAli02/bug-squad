# Curated OSS bug cases

15 closed, bug-labeled issues from five repositories were rechecked. All 15 passed: an MIT or Apache-2.0 license was read at the exact source snapshot, a linked fix was merged or identified as the closing commit, each diff changes 2–5 files, and each changes at least one upstream test. **Dropped candidates: none of the 15 previously shortlisted cases.**

Every focused reproduction fails on its pre-fix snapshot and passes when the exact upstream source changes are applied in a temporary copy. This is focused validation, not a claim that the entire upstream test suite passes. Arrow #1078 and #996 have related locale additions in their small fixes; their bug behavior was reproduced independently.

## Layout and provenance

- `<repo>/bug0X_ticket.md`: independently written ticket and reproduction steps.
- `<repo>/bug0X_fix_commit.txt`: exact full fix URL followed by the full SHA; no commit prose.
- `<repo>/bug0X_files.txt`: original upstream paths, relative to `<repo>/bug0X/upstream/`.
- `<repo>/bug0X/upstream/`: byte-for-byte files from the fix's **first parent**, plus that snapshot's license. No upstream Git repositories, histories, issue attachments, or full test suites are included.
- `<repo>/bug0X/provenance.json`: parent SHA, fix and license links, changed upstream tests, diff counts, and SHA-256 hashes of every copied source file.
- `<repo>/bug0X/reproduce.py` or `reproduce.js`: original minimal reproductions using synthetic inputs.

Runtime modules imported by each reproduction are included so the excerpts run without an installed copy of the target library. Dependency modules within that library are retained where necessary. Yup type-only declarations are omitted; the runner transpiles the selected code without type-checking it. Third-party dependencies are installed separately and are not vendored.

Original license and source attribution notices are preserved. No reporter profiles, copied issue prose, original diagnostic logs, or commit messages are included. This is an audit of the selected excerpts, not certification of the entire upstream history.

## Python setup

From the repository root, create an isolated environment (outside the checkout if preferred):

```sh
python3 -m venv /tmp/bug-squad-oss-venv
. /tmp/bug-squad-oss-venv/bin/activate
python3 -m pip install -r oss_cases/requirements.txt
python3 oss_cases/attrs/bug01/reproduce.py
```

Validated with CPython 3.14.4 and the versions in `requirements.txt`. The attrs and schedule cases need only the standard library; Arrow and jsonschema need the listed dependencies. Each script puts its own source snapshot first on the import path. Run each script in a fresh process.

## JavaScript setup

```sh
npm ci --prefix oss_cases/yup --ignore-scripts --no-audit --no-fund
node oss_cases/yup/run.cjs bug01
```

Validated with Node.js 22.22.1 and esbuild 0.25.12. The dependency lockfile is included. The runner writes its temporary bundle outside the checkout and removes it after execution.

## Reading results

The reproductions assert correct behavior: a bug-specific exception or assertion failure is the expected result **before** the fix. A missing-module/import error, dependency-install error, or build failure does not count as reproducing a bug. A reproduction should exit 0 after the associated upstream fix. Do not replace the checked-in buggy files with fixed code when using these as baseline cases.

The `changed_test_files` in each provenance file are the actual upstream test paths changed by the fix. They are ground-truth references for Blast Radius, not tests copied into this dataset.

## Cases

| Case | Upstream issue | Ticket | Fix files |
|---|---|---|---:|
| attrs/bug01 | [python-attrs/attrs #1348](https://github.com/python-attrs/attrs/issues/1348) | [A nullable conversion pipeline rejects supplied values](attrs/bug01_ticket.md) | 3 |
| attrs/bug02 | [python-attrs/attrs #1327](https://github.com/python-attrs/attrs/issues/1327) | [Reassigning a field with chained converters raises an internal error](attrs/bug02_ticket.md) | 5 |
| attrs/bug03 | [python-attrs/attrs #1284](https://github.com/python-attrs/attrs/issues/1284) | [A defaulted keyword-only field prevents class creation with a pre-init hook](attrs/bug03_ticket.md) | 3 |
| jsonschema/bug01 | [python-jsonschema/jsonschema #1328](https://github.com/python-jsonschema/jsonschema/issues/1328) | [Inspecting a valid array position changes the error index](jsonschema/bug01_ticket.md) | 3 |
| jsonschema/bug02 | [python-jsonschema/jsonschema #1157](https://github.com/python-jsonschema/jsonschema/issues/1157) | [Mixed-type excess array values interrupt validation error reporting](jsonschema/bug02_ticket.md) | 4 |
| jsonschema/bug03 | [python-jsonschema/jsonschema #1125](https://github.com/python-jsonschema/jsonschema/issues/1125) | [Extending a legacy validator changes reference-sibling handling](jsonschema/bug03_ticket.md) | 3 |
| schedule/bug01 | [dbader/schedule #304](https://github.com/dbader/schedule/issues/304) | [A daily job finishing after midnight misses its next evening run](schedule/bug01_ticket.md) | 2 |
| schedule/bug02 | [dbader/schedule #286](https://github.com/dbader/schedule/issues/286) | [An hourly schedule loses the requested seconds component](schedule/bug02_ticket.md) | 2 |
| schedule/bug03 | [dbader/schedule #190](https://github.com/dbader/schedule/issues/190) | [Formatting a job that receives itself as an argument recurses](schedule/bug03_ticket.md) | 2 |
| yup/bug01 | [jquense/yup #1423](https://github.com/jquense/yup/issues/1423) | [Concatenation forgets an object schema's dependency exclusions](yup/bug01_ticket.md) | 3 |
| yup/bug02 | [jquense/yup #343](https://github.com/jquense/yup/issues/343) | [Ensuring an array discards a scalar input](yup/bug02_ticket.md) | 2 |
| yup/bug03 | [jquense/yup #1160](https://github.com/jquense/yup/issues/1160) | [Combining schemas removes an existing label and metadata](yup/bug03_ticket.md) | 2 |
| arrow/bug01 | [arrow-py/arrow #1015](https://github.com/arrow-py/arrow/issues/1015) | [An empty humanization unit selection raises the wrong exception](arrow/bug01_ticket.md) | 2 |
| arrow/bug02 | [arrow-py/arrow #1078](https://github.com/arrow-py/arrow/issues/1078) | [Czech and Slovak humanization fail when a selected unit is zero](arrow/bug02_ticket.md) | 4 |
| arrow/bug03 | [arrow-py/arrow #996](https://github.com/arrow-py/arrow/issues/996) | [A past timestamp is described as future when zero-valued units are included](arrow/bug03_ticket.md) | 4 |
