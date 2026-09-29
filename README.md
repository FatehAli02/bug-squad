# 🐛 Bug Squad

> **Autonomous End-to-End Bug Fixing and Change-Impact Analysis Powered by IBM Bob 2.0**

Bug Squad is an AI-powered development pipeline built for the **IBM Bob 2.0 Hackathon**. It takes raw bug tickets and turns them into thoroughly tested, reviewed pull requests while safeguarding codebases against unintended ripple effects using **Blast Radius**—a static dependency-impact analyzer.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Architecture & Workflow](#-architecture--workflow)
  - [The 4-Subagent Pipeline](#the-4-subagent-pipeline)
  - [Blast Radius: Change-Impact Analysis](#blast-radius-change-impact-analysis)
  - [Bobcoin Discipline](#bobcoin-discipline)
- [Repository Structure](#-repository-structure)
- [Components](#-components)
  - [1. Sample Application (Expense Tracker)](#1-sample-application-expense-tracker)
  - [2. Blast Radius Static Engine](#2-blast-radius-static-engine)
  - [3. Curated OSS Benchmark Cases](#3-curated-oss-benchmark-cases)
  - [4. Interactive Streamlit Dashboard](#4-interactive-streamlit-dashboard)
- [Getting Started & Installation](#-getting-started--installation)
  - [Prerequisites](#prerequisites)
  - [Environment Setup](#environment-setup)
  - [Using Dev Containers / GitHub Codespaces](#using-dev-containers--github-codespaces)
- [How to Run](#-how-to-run)
  - [1. Launch the Interactive Dashboard](#1-launch-the-interactive-dashboard)
  - [2. Run Blast Radius (Impact Scan)](#2-run-blast-radius-impact-scan)
  - [3. Run the Sample Application (CLI)](#3-run-the-sample-application-cli)
  - [4. Execute Sample App Tests](#4-execute-sample-app-tests)
  - [5. Run OSS Reproductions](#5-run-oss-reproductions)
- [Tracked Bugs Benchmark](#-tracked-bugs-benchmark)
  - [Sample App Seeded Bugs](#sample-app-seeded-bugs)
  - [Open Source Real-World Bugs](#open-source-real-world-bugs)
- [Compliance & Data Safety](#-compliance--data-safety)

---

## 🌟 Overview

Fixing bugs in production software is high-friction and error-prone: developers must reproduce the issue, trace the root cause across call graphs, craft a patch, verify regressions, and draft documentation.

**Bug Squad** automates this entire lifecycle using two core pillars:

1. **Autonomous 4-Role Subagent Squad**: IBM Bob subagents operate in sequence with isolated tasks and well-defined file-based handoffs:
   - **`🔴 Reproducer`** ➔ Writes a minimal failing test proving the bug.
   - **`🔍 Investigator`** ➔ Diagnoses root causes and measures pre-fix blast radius.
   - **`🔧 Fixer`** ➔ Iteratively implements fixes until all unit and regression tests pass.
   - **`✅ Reviewer`** ➔ Performs post-fix blast radius audits and generates complete pull request documentation.
2. **Blast Radius (Change-Impact Analyzer)**:
   - A hybrid static-analysis and LLM reasoning engine.
   - Combines Python AST call/import/subclass graph construction with Bob's semantic reasoning to classify risks (High / Medium / Low) and flag untested dependencies.

---

## 🏗 Architecture & Workflow

### The 4-Subagent Pipeline

```
┌────────────────────────────────────────────────────────┐
│               Bug Ticket + Logs + Spec                │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ 🔴 Reproducer     │  Writes failing test proving bug
                  └────────┬─────────┘  (sample_app/tests/test_bugs.py)
                           │
                           ▼
                  ┌──────────────────┐
                  │ 🔍 Investigator   │  Finds root cause + runs Blast Radius
                  └────────┬─────────┘  (graph.json, impact_plan.json)
                           │
                           ▼
                  ┌──────────────────┐
                  │ 🔧 Fixer         │  Patches code until tests pass
                  └────────┬─────────┘  (FIXER_OUTPUT_bugXX.md)
                           │
                           ▼
                  ┌──────────────────┐
                  │ ✅ Reviewer      │  Re-runs Blast Radius (graph_after.json)
                  └────────┬─────────┘  Audits regressions & writes PR desc
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             Reviewed, Tested Pull Request              │
└────────────────────────────────────────────────────────┘
```

#### Handoff Artifacts Between Tasks

| Pipeline Stage | Output Artifact | Consumed By | Description |
|:---|:---|:---|:---|
| **Reproducer** | `sample_app/tests/test_bugs.py` | Fixer, Reviewer | Minimal failing test cases proving bug presence |
| **Investigator**| `impact_plan.json` | Fixer, Reviewer | Root cause analysis, targeted symbols, risk level |
| **Investigator**| `blast_radius/graph.json` | Fixer, Reviewer | Pre-fix dependency call/import graph |
| **Fixer** | `FIXER_OUTPUT_bugXX.md` | Reviewer | Patch summary, files edited, test validation log |
| **Reviewer** | `blast_radius/graph_after.json` | Reviewer | Post-fix dependency graph (diffed against pre-fix) |
| **Reviewer** | `PR_DESCRIPTION_bugXX.md` | Developers / CI | Comprehensive PR title, summary, and verification details |

### Blast Radius: Change-Impact Analysis

Blast Radius operates in two complementary stages:

1. **Static Graph Extraction (`blast_radius/scan.py`)**:
   - Parses the codebase AST (Abstract Syntax Tree) to extract direct callers (`calls`), module imports (`imports`), and inheritance hierarchies (`subclasses`) targeting any specified symbol.
   - Zero external dependencies: runs purely on Python standard library modules.
2. **Semantic Risk Reasoning (IBM Bob)**:
   - Evaluates the extracted graph nodes to distinguish harmless calls from breaking behavioural mutations (e.g. signature alterations, modified return values, off-by-one edge cases).
   - Generates risk ratings (High / Medium / Low) with actionable rationales and flags untested code paths.

### Bobcoin Discipline

In strict compliance with Bob hackathon resource limits (40 Bobcoins per person):
- **Bobcoins Used**: High-value reasoning only (Reproducer, Investigator, Fixer, Reviewer subagents, and LLM graph risk classification).
- **Plain Code (Zero Bobcoins)**: Static AST dependency scanning (`blast_radius/scan.py`), the interactive Streamlit dashboard (`dashboard/app.py`), local unit testing, and data curation.

---

## 📁 Repository Structure

```
bug-squad/
├── .devcontainer/              # VS Code / Codespaces dev container configuration
│   └── devcontainer.json
├── blast_radius/               # Blast Radius static impact analyzer
│   ├── scan.py                 # Core AST scanner (calls, imports, subclasses)
│   ├── graph.json              # Pre-fix call/dependency graph
│   └── graph_after.json        # Post-fix call/dependency graph (diffed)
├── bob_sessions/               # Screenshots of subagent Bob sessions
├── bugs/                       # Bug tickets and ground truth
│   ├── ticket_01.md ... 05.md  # Synthetic bug tickets for sample_app
│   └── answer_key.md           # Ground truth root causes & fixes
├── dashboard/                  # Streamlit metrics and visualization dashboard
│   ├── app.py                  # Main interactive dashboard application
│   └── requirements.txt        # Dashboard dependencies (streamlit, pandas)
├── oss_cases/                  # 15 Curated real-world OSS bug benchmark cases
│   ├── attrs/                  # python-attrs issues (#1348, #1327, #1284)
│   ├── schedule/               # dbader/schedule issues (#304, #286, #190)
│   ├── jsonschema/             # python-jsonschema issues (#1328, #1157, #1125)
│   ├── arrow/                  # arrow-py issues (#1015, #1078, #996)
│   ├── yup/                    # jquense/yup issues (#1423, #343, #1160)
│   ├── requirements.txt        # Python OSS case dependencies
│   └── README.md               # Detailed OSS case documentation
├── sample_app/                 # Seeded base expense-tracker application
│   ├── __init__.py
│   ├── api.py                  # ExpenseTracker business logic
│   ├── main.py                 # CLI interface with subcommands
│   ├── models.py               # Expense & Budget dataclasses, JSON storage
│   ├── utils.py                # Date manipulation, filtering, CSV export
│   └── tests/                  # Pytest test suite (baseline + reproducers)
│       ├── test_api.py         # API tests
│       ├── test_models.py      # Model tests
│       └── test_bugs.py        # Reproducer regression tests
├── AGENTS.md                   # Agent guidelines, style, and critical gotchas
├── CONTEXT.md                  # Project context document for Bob subagents
├── DATA_SOURCES.md             # Compliance log & licensing provenance
├── FIXER_OUTPUT_bug01..04.md   # Fixer subagent logs and diff summaries
├── PR_DESCRIPTION_bug02..04.md # Reviewer subagent generated PR descriptions
├── REPRODUCER_OUTPUT*.md       # Reproducer test output and evidence logs
└── impact_plan.json            # Structured impact analysis plan
```

---

## 🧩 Components

### 1. Sample Application (Expense Tracker)
A self-contained Python CLI application in `sample_app/` that manages personal expenses and category budgets. It features:
- Expense CRUD operations with JSON persistence (`models.py`).
- Budget checking and spending alerts (`api.py`).
- Date ranges, monthly aggregation, and CSV export (`utils.py`).
- CLI commands (`main.py`): `add`, `list`, `update`, `delete`, `budget`, `report`, `export`, and `trend`.

### 2. Blast Radius Static Engine
Located in `blast_radius/scan.py`. It inspects Python files via standard library `ast` without executing code, locating references to target symbols across modules, functions, and classes.

### 3. Curated OSS Benchmark Cases
Located in `oss_cases/`. Contains 15 real-world bugs extracted from five permissively-licensed projects (MIT / Apache 2.0). Every case contains:
- Exact byte-for-byte upstream code at the bug snapshot (`upstream/`).
- Minimal reproduction scripts (`reproduce.py` or `reproduce.js`).
- Provenance documentation with first-parent SHAs and changed upstream test references (`provenance.json`).

### 4. Interactive Streamlit Dashboard
Located in `dashboard/app.py`. Offers a multi-page interactive web application displaying:
- **🏠 Overview**: High-level KPIs (bugs resolved, tests added, regressions prevented).
- **🔄 Pipeline**: Visual 4-stage pipeline execution, handoff artifacts, and Bobcoin usage.
- **🐞 Sample App Bugs**: Root cause, fix details, risk levels, and test progression charts.
- **📦 OSS Cases**: Filtering and exploration across all 15 open-source bug benchmarks.
- **💥 Blast Radius**: Interactive before-and-after graph inspection highlighting new edges.
- **🗂 Impact Table**: Risk classification matrix and test coverage tracking.

---

## 🚀 Getting Started & Installation

### Prerequisites

- **Python**: Version 3.10 or higher.
- **Node.js**: Version 18+ (required only if testing JavaScript OSS cases under `oss_cases/yup`).
- **Git**

### Environment Setup

1. **Clone the repository**:
   ```sh
   git clone https://github.com/FatehAli02/bug-squad.git
   cd bug-squad
   ```

2. **Create and activate a virtual environment**:
   ```sh
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```sh
   # Install test runner
   python -m pip install pytest

   # Install Dashboard requirements
   python -m pip install -r dashboard/requirements.txt

   # (Optional) Install Python OSS cases dependencies
   python -m pip install -r oss_cases/requirements.txt

   # (Optional) Install Yup JavaScript dependencies
   npm ci --prefix oss_cases/yup --ignore-scripts --no-audit --no-fund
   ```

### Using Dev Containers / GitHub Codespaces

This repository includes a ready-to-use Dev Container configuration (`.devcontainer/devcontainer.json`).
- Open the repository in **VS Code** with the **Dev Containers** extension installed, and select **"Reopen in Container"**.
- Or open directly in **GitHub Codespaces**.
- The environment will automatically configure Python 3.11, install all requirements, and expose the dashboard on port `8501`.

---

## 💻 How to Run

### 1. Launch the Interactive Dashboard

To start the Streamlit web dashboard:

```sh
streamlit run dashboard/app.py
```

Then open your browser at `http://localhost:8501`.

---

### 2. Run Blast Radius (Impact Scan)

To analyze the impact radius of any function or symbol before or after modifying it:

```sh
# Scan before making a code change
python blast_radius/scan.py \
  --repo sample_app \
  --target utils.month_date_range \
  --out blast_radius/graph.json

# Scan after making a code change
python blast_radius/scan.py \
  --repo sample_app \
  --target utils.month_date_range \
  --out blast_radius/graph_after.json
```

**Target Format Options**:
- Fully-qualified: `--target utils.month_date_range`
- Bare symbol name: `--target month_date_range`
- Class name: `--target ExpenseTracker`

---

### 3. Run the Sample Application (CLI)

The sample app can be run directly using Python without external packages:

```sh
# Add expenses
python sample_app/main.py add --title "Coffee" --amount 3.50 --category food
python sample_app/main.py add --title "Metro Pass" --amount 45.00 --category transport
python sample_app/main.py add --title "Internet" --amount 60.00 --category utilities

# List all expenses
python sample_app/main.py list

# Filter expenses by month
python sample_app/main.py list --month 2024-05

# Set and check monthly budget
python sample_app/main.py budget --set food 150.00 2024-05
python sample_app/main.py budget --check food 2024-05

# Generate monthly spending report
python sample_app/main.py report --month 2024-05

# Export expenses to CSV
python sample_app/main.py export --out my_expenses.csv

# View spending trends
python sample_app/main.py trend --months 3
```

> **Tip**: You can specify a custom JSON storage path using `--store <file.json>` before the subcommand:
> ```sh
> python sample_app/main.py --store my_store.json list
> ```

---

### 4. Execute Sample App Tests

Unit tests are written with `pytest`. **Always run pytest from the repository root**:

```sh
# Run all sample app tests (models, API, and regression tests)
pytest sample_app/tests/ -v

# Run only the Reproducer regression tests
pytest sample_app/tests/test_bugs.py -v

# Run a specific test case
pytest sample_app/tests/test_api.py::TestBudget::test_check_budget_under -v
```

---

### 5. Run OSS Reproductions

The curated OSS cases validate Blast Radius against real-world library bugs.

> ⚠️ **Important Gotcha**: OSS reproduction tests are designed to **FAIL** on the pre-fix snapshot. A failing test proves the bug has been successfully reproduced.

#### Python Cases (`attrs`, `schedule`, `jsonschema`, `arrow`)
```sh
# Run an individual reproduction script directly
python oss_cases/attrs/bug01/reproduce.py
python oss_cases/schedule/bug01/reproduce.py
python oss_cases/jsonschema/bug01/reproduce.py
python oss_cases/arrow/bug01/reproduce.py

# Run all Python OSS test suites via pytest
pytest oss_cases/attrs/test_bugs.py \
       oss_cases/schedule/test_bugs.py \
       oss_cases/jsonschema/test_bugs.py \
       oss_cases/arrow/test_bugs.py -v
```

#### JavaScript Cases (`yup`)
```sh
# Run via the provided esbuild runner
node oss_cases/yup/run.cjs bug01
node oss_cases/yup/run.cjs bug02
node oss_cases/yup/run.cjs bug03

# Or execute via the pytest wrapper
pytest oss_cases/yup/test_bugs.py -v
```

---

## 📊 Tracked Bugs Benchmark

### Sample App Seeded Bugs

| ID | Title | File / Symbol | Root Cause | Risk | Status |
|:---|:---|:---|:---|:---:|:---:|
| **BUG 01** | Last day of month excluded | `sample_app/utils.py`<br>`month_date_range` | End boundary calculated with `- 1`, dropping month-end expenses | High | ✅ Fixed |
| **BUG 02** | Missing None-check | `sample_app/api.py`<br>`update_expense` | Dereferenced `.title` on `None` when expense ID not found | High | ✅ Fixed |
| **BUG 03** | Budget overage rounding error | `sample_app/api.py`<br>`over_budget_categories` | Filtered on `percent_used > 100`; rounding caused `$0.01` overspend to show `100.0%` | High | ✅ Fixed |
| **BUG 04** | Mutable default parameter | `sample_app/utils.py`<br>`to_csv_rows` | Parameter `headers=[]` retained appended headers across calls | High | ✅ Fixed |
| **BUG 05** | Timezone clock skew | `sample_app/main.py`<br>`_today_utc` | `datetime.now(timezone.utc)` lagged local dates in UTC+ zones | Medium | ✅ Fixed |

---

### Open Source Real-World Bugs

| Library | Issue | Title | Upstream Commit | Risk |
|:---|:---|:---|:---|:---:|
| **attrs** | [#1348](https://github.com/python-attrs/attrs/issues/1348) | Nullable conversion pipeline rejects supplied values | `e21793e` | High |
| **attrs** | [#1327](https://github.com/python-attrs/attrs/issues/1327) | Reassigning field with chained converters raises error | `6fda0a4` | High |
| **attrs** | [#1284](https://github.com/python-attrs/attrs/issues/1284) | Defaulted kw_only field + pre-init hook SyntaxError | `09161fc` | High |
| **schedule**| [#304](https://github.com/dbader/schedule/issues/304) | Daily job finishing after midnight misses next evening run | `4a36c6e` | Medium |
| **schedule**| [#286](https://github.com/dbader/schedule/issues/286) | Hourly schedule drops specified seconds component | `1dab2d4` | Medium |
| **schedule**| [#190](https://github.com/dbader/schedule/issues/190) | Formatting job that receives itself causes infinite recursion | `a19e5c2` | Low |
| **jsonschema**| [#1328](https://github.com/python-jsonschema/jsonschema/issues/1328) | Valid array position alters error index in unevaluatedItems | `f58b09e` | High |
| **jsonschema**| [#1157](https://github.com/python-jsonschema/jsonschema/issues/1157) | Mixed-type excess array values interrupt error reporting | `d724e81` | High |
| **jsonschema**| [#1125](https://github.com/python-jsonschema/jsonschema/issues/1125) | Extending legacy validator changes reference sibling behavior | `9c8a14b` | High |
| **arrow** | [#1015](https://github.com/arrow-py/arrow/issues/1015) | Empty humanization unit selection raises wrong exception | `b214df9` | Low |
| **arrow** | [#1078](https://github.com/arrow-py/arrow/issues/1078) | Czech and Slovak humanization fail when unit is zero | `e185cf1` | Medium |
| **arrow** | [#996](https://github.com/arrow-py/arrow/issues/996) | Past timestamp described as future with zero-valued units | `40cbb8a` | Low |
| **yup** | [#1423](https://github.com/jquense/yup/issues/1423) | Concatenation drops object dependency exclusions | `e2a4df8` | High |
| **yup** | [#343](https://github.com/jquense/yup/issues/343) | Ensuring an array discards scalar input | `7f41a02` | Medium |
| **yup** | [#1160](https://github.com/jquense/yup/issues/1160) | Combining schemas removes existing label and metadata | `5b18cd3` | High |

---

## 🔒 Compliance & Data Safety

This repository strictly adheres to open-source governance and hackathon data compliance rules:
- **Zero Confidential / PII Data**: Contains no client data, company confidential materials, personally identifiable information, or social media data.
- **Permissive Open Source Licenses**: All benchmark cases are sourced from verified **MIT** or **Apache-2.0** repositories. Full provenance, commit hashes, and licenses are documented in [`DATA_SOURCES.md`](DATA_SOURCES.md) and individual `provenance.json` files.
- **Isolated Snapshots**: Only minimal excerpts necessary to reproduce the specific issues are included; full upstream Git histories and issue discussion threads are excluded.
