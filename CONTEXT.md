# CONTEXT.md — Read this before starting any Bob task

This file exists so every Bob IDE session has the same understanding of the
project, no matter who starts it or which subagent role it's running. If
you're a Bob task starting fresh, read this whole file first.

---

## 1. What we're building

**Bug Squad** — an IBM Bob-powered pipeline that takes a bug ticket and turns
it into a reviewed, tested pull request, while also predicting what the fix
could break elsewhere.

Two things live in this repo:
1. **The subagent pipeline** — four roles (Reproducer, Investigator, Fixer,
   Reviewer) that hand work to each other in sequence.
2. **Blast Radius** — a change-impact analyzer. Before and after a fix, it
   answers: "If I change this code, what else could break?"

This is a hackathon project for the IBM Bob 2.0 Hackathon. It must showcase
Bob IDE as a core component (Agent mode, subagents, parallel tasks, document
understanding).

---

## 2. The pipeline (who does what, in order)

```
Bug ticket + logs + spec
        │
        ▼
  Reproducer  → writes a failing test that proves the bug
        │
        ▼
  Investigator → finds root cause + runs Blast Radius (before-fix scope)
        │
        ▼
  Fixer       → patches code until tests pass
        │
        ▼
  Reviewer    → re-runs Blast Radius (after-fix check), writes PR description
```

Each role is a **separate Bob task**. A task only knows what's in its own
prompt plus files in this repo — it does not automatically see what a
previous task did. That's why every subagent prompt tells you exactly what
inputs to expect and what output to hand off, and why outputs from one step
(e.g. the Reproducer's failing test) should be saved as real files in the
repo so the next step can read them.

---

## 3. Blast Radius, in detail

Blast Radius has two halves:

- **Static scan (plain code, not Bob):** a Python `ast` / tree-sitter script
  builds a call/dependency graph of the codebase and saves it as
  `graph.json` (before the fix) or `graph_after.json` (after the fix).
- **Bob's reasoning (Agent mode):** Bob reads the graph and judges what
  actually breaks — not just "this file imports that function" but "this
  caller assumes the old return type." It rates each impacted item
  High/Medium/Low risk with a one-line reason, and flags which impacted
  items have no test coverage.

Output: an impact table (file, function, risk, reason, covering tests) and,
after the fix, a before/after comparison highlighting any new regressions.

---

## 4. Data we use (and don't use)

- **Seeded sample app:** an original small app we wrote ourselves, with
  deliberately seeded bugs. Tickets/logs/specs for these are synthetic.
- **Real open-source bugs:** closed issues + their fix commits from
  permissively licensed repos (MIT / Apache / BSD only). Every source is
  logged in `DATA_SOURCES.md`.
- **Never:** client data, company confidential data, personal information,
  or anything scraped from social media.

We use real fix commits as ground truth — comparing what Blast Radius
predicts against what the maintainers actually changed.

---

## 5. Tech stack

- **IBM Bob IDE** — Agent mode, subagents, parallel tasks, document
  understanding. (Bob Shell is not used, to conserve Bobcoins.)
- **Python** (`ast` or tree-sitter) — the static graph builder behind Blast
  Radius.
- **A lightweight dashboard** — shows time saved, tests added, and Blast
  Radius precision/recall against real fix commits.

---

## 6. Repo layout (expected)

```
/bob_sessions/        # required: PNG screenshots of every Bob task's
                       # session summary (see hackathon rules)
/sample_app/           # seeded base app with known bugs
/oss_cases/            # cloned/excerpted OSS bugs used for validation
/blast_radius/         # static scan script + graph outputs
/dashboard/            # results dashboard
DATA_SOURCES.md        # every external repo/site used + license
CONTEXT.md             # this file
```

---

## 7. Bobcoin discipline

The team has 40 Bobcoins per person. Static scanning, dashboard building, and
data curation should be done in plain code, not inside Bob tasks. Only the
four subagent roles (Reproducer, Investigator, Fixer, Reviewer) and Blast
Radius's reasoning step should consume Bobcoins.

---

## 8. Your job right now

If you were pointed here from a subagent prompt, go back to that prompt now —
it tells you which of the four roles you're playing and exactly what to do.
This file is background only; the task-specific prompt is where your actual
instructions are.
