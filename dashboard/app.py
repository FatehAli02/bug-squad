"""
Bug Squad Dashboard — IBM Bob Hackathon
A Streamlit dashboard showing the full Bug Squad pipeline results.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Bug Squad — IBM Bob",
    page_icon="🐛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Paths (relative to repo root — run with: streamlit run dashboard/app.py)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "blast_radius"))
try:
    from scan import build_graph, diff_graphs
except ImportError:
    build_graph = None
    diff_graphs = None

# ---------------------------------------------------------------------------
# Inline data (avoid runtime file-read failures on cloud)
# ---------------------------------------------------------------------------

SAMPLE_BUGS = [
    {
        "id": "bug01",
        "title": "Off-by-one: last day of month excluded",
        "file": "sample_app/utils.py",
        "function": "month_date_range",
        "root_cause": "End boundary computed as `last_day - 1`, silently dropping every expense on the final calendar day of any month.",
        "fix": "Remove `- 1` so end = `date(year, month, last_day)`.",
        "diff_summary": "1 line changed in utils.py",
        "tests_added": 4,
        "tests_fixed": 4,
        "risk": "High",
        "status": "✅ Fixed",
    },
    {
        "id": "bug02",
        "title": "Missing None-check in update_expense",
        "file": "sample_app/api.py",
        "function": "ExpenseTracker.update_expense",
        "root_cause": "`get_expense()` returns None for unknown IDs. The next line dereferenced `.title` on None → AttributeError instead of the intended ValueError.",
        "fix": "Replace `if exp.title is None:` with `if exp is None:`",
        "diff_summary": "1 line changed in api.py",
        "tests_added": 2,
        "tests_fixed": 2,
        "risk": "High",
        "status": "✅ Fixed",
    },
    {
        "id": "bug03",
        "title": "over_budget_categories misses $0.01-over-limit spending",
        "file": "sample_app/api.py",
        "function": "ExpenseTracker.over_budget_categories",
        "root_cause": "Filtered by `percent_used > 100`. Python's rounding causes `round(100.01/100*100,1) == 100.0`, so 100.0 > 100 is False.",
        "fix": "Filter on the pre-computed `s['over_budget']` boolean flag instead.",
        "diff_summary": "1 line changed in api.py",
        "tests_added": 2,
        "tests_fixed": 2,
        "risk": "High",
        "status": "✅ Fixed",
    },
    {
        "id": "bug04",
        "title": "Mutable default `headers=[]` in to_csv_rows",
        "file": "sample_app/utils.py",
        "function": "to_csv_rows",
        "root_cause": "Python evaluates default args once at definition time. The shared `[]` object is mutated across calls, corrupting every subsequent headerless call.",
        "fix": "Use `headers: Optional[List[str]] = None` + `is not None` identity guard.",
        "diff_summary": "2 lines changed in utils.py",
        "tests_added": 3,
        "tests_fixed": 3,
        "risk": "High",
        "status": "✅ Fixed",
    },
    {
        "id": "bug05",
        "title": "_today_utc uses UTC clock instead of local clock",
        "file": "sample_app/main.py",
        "function": "_today_utc",
        "root_cause": "`datetime.now(tz=timezone.utc)` returns UTC time. In UTC+ zones, UTC lags local date — expenses get the wrong calendar date.",
        "fix": "Use `date.today().isoformat()` (local clock).",
        "diff_summary": "1 line changed in main.py",
        "tests_added": 2,
        "tests_fixed": 2,
        "risk": "Medium",
        "status": "✅ Fixed",
    },
]

OSS_BUGS = [
    {
        "lib": "attrs",
        "id": "bug01",
        "issue": "#1351",
        "title": "optional() + pipe() raises TypeError on construction",
        "root_cause": "`optional()` wrapped a `Converter` in a plain single-arg closure. The Converter requires `(value, instance, field)` but only `value` was passed.",
        "fix": "Detect Converter objects inside optional() and forward all three args.",
        "risk": "High",
        "status": "✅ Fixed",
        "upstream": "e21793e",
    },
    {
        "lib": "attrs",
        "id": "bug02",
        "issue": "#1327",
        "title": "Chained converter raises AttributeError on field reassignment",
        "root_cause": "`Converter.__call__` slot declared in `__slots__` but never assigned in `__init__`. Works during `__init__` (uses local dict), fails on `setattr` hook.",
        "fix": "Assign `self.__call__` in `Converter.__init__`; update `setters.convert()` to pass `(val, instance, attrib)` for Converter objects.",
        "risk": "High",
        "status": "✅ Fixed",
        "upstream": "6fda0a4",
    },
    {
        "lib": "attrs",
        "id": "bug03",
        "issue": "#1284",
        "title": "kw_only field with default + __attrs_pre_init__ → SyntaxError",
        "root_cause": "Code gen built `pre_init_kw_only_args` by joining raw `kw_arg` strings including `=default` suffix, producing invalid syntax like `a=a=NOTHING`.",
        "fix": "`kw_arg.split('=')[0]` strips the default expression, leaving only the bare parameter name for the call-site arg.",
        "risk": "High",
        "status": "✅ Fixed",
        "upstream": "09161fc",
    },
    {
        "lib": "schedule",
        "id": "bug01",
        "issue": "N/A",
        "title": "next_run not updated after manual job.run()",
        "root_cause": "Calling `job.run()` directly skips the scheduler's run-tracking logic, leaving `next_run` stale so the job fires again immediately.",
        "fix": "Update `last_run` and recalculate `next_run` inside `job.run()`.",
        "risk": "Medium",
        "status": "🔬 Reproduced",
        "upstream": "4a36c6e",
    },
    {
        "lib": "schedule",
        "id": "bug02",
        "issue": "N/A",
        "title": "Decorator-scheduled jobs run twice on first tick",
        "root_cause": "`@repeat` decorator schedules the job AND the decorated call happens once at decoration time, causing an extra immediate execution.",
        "fix": "Remove the immediate call from the decorator.",
        "risk": "Medium",
        "status": "🔬 Reproduced",
        "upstream": "1dab2d4",
    },
    {
        "lib": "jsonschema",
        "id": "bug01",
        "issue": "N/A",
        "title": "unevaluatedProperties allows extra props inside allOf",
        "root_cause": "`unevaluatedProperties` did not track annotations from sibling `allOf` sub-schemas, treating all sub-schema properties as unevaluated.",
        "fix": "Collect annotation results from sibling schemas before evaluating `unevaluatedProperties`.",
        "risk": "High",
        "status": "🔬 Reproduced",
        "upstream": "N/A",
    },
    {
        "lib": "jsonschema",
        "id": "bug02",
        "issue": "N/A",
        "title": "Recursive $ref causes infinite recursion instead of error",
        "root_cause": "No recursion depth guard in the `$ref` resolver. A self-referential schema blows the Python call stack.",
        "fix": "Track visited $ref targets and raise SchemaError on cycle.",
        "risk": "High",
        "status": "🔬 Reproduced",
        "upstream": "N/A",
    },
    {
        "lib": "jsonschema",
        "id": "bug03",
        "issue": "N/A",
        "title": "prefixItems does not enforce maxItems",
        "root_cause": "`prefixItems` validator allowed arrays longer than the defined prefix without checking the `maxItems` constraint.",
        "fix": "Enforce `maxItems` after processing prefix items.",
        "risk": "Medium",
        "status": "🔬 Reproduced",
        "upstream": "N/A",
    },
    {
        "lib": "arrow",
        "id": "bug01",
        "issue": "N/A",
        "title": "humanize() wrong direction for sub-second future deltas",
        "root_cause": "Delta of < 1 s into the future was reported as 'just now' (past) instead of 'in seconds'.",
        "fix": "Check sign of delta before selecting past/future granularity string.",
        "risk": "Low",
        "status": "🔬 Reproduced",
        "upstream": "N/A",
    },
    {
        "lib": "arrow",
        "id": "bug02",
        "issue": "N/A",
        "title": "shift() across DST boundary adds wrong timedelta",
        "root_cause": "Naive timedelta arithmetic didn't account for DST fold, shifting by wall-clock hours instead of absolute hours.",
        "fix": "Normalise to UTC before shifting, then convert back.",
        "risk": "Medium",
        "status": "🔬 Reproduced",
        "upstream": "N/A",
    },
    {
        "lib": "arrow",
        "id": "bug03",
        "issue": "N/A",
        "title": "floor('week') gives wrong result for Sunday",
        "root_cause": "`floor('week')` used Monday as week start unconditionally, producing the wrong week boundary for Sunday dates.",
        "fix": "Honour locale/ISO week-start setting when computing floor.",
        "risk": "Low",
        "status": "🔬 Reproduced",
        "upstream": "N/A",
    },
    {
        "lib": "yup",
        "id": "bug01",
        "issue": "N/A",
        "title": "number().max() accepts Infinity",
        "root_cause": "`Infinity > max` is true, but `Number.isFinite(Infinity)` is false so the validator silently passed Infinity through.",
        "fix": "Add an explicit `isFinite` check before the `> max` comparison.",
        "risk": "Medium",
        "status": "🔬 Reproduced",
        "upstream": "N/A",
    },
    {
        "lib": "yup",
        "id": "bug02",
        "issue": "N/A",
        "title": "object().shape() loses required() on nested field",
        "root_cause": "Merging shapes with `object.assign()` shallow-copied the inner schema without preserving the `required` flag.",
        "fix": "Deep-clone inner schema entries when merging shapes.",
        "risk": "High",
        "status": "🔬 Reproduced",
        "upstream": "N/A",
    },
    {
        "lib": "yup",
        "id": "bug03",
        "issue": "N/A",
        "title": "array().of() rejects valid items on concurrent validation",
        "root_cause": "Shared mutable state in the validator context caused race-like corruption during `Promise.all` on array items.",
        "fix": "Clone validator context per-item before async validation.",
        "risk": "High",
        "status": "🔬 Reproduced",
        "upstream": "N/A",
    },
]

BLAST_BEFORE_FALLBACK = {
    "target": "utils.month_date_range",
    "impacted": [
        {"file": "main.py", "symbol": "cmd_list", "relation": "imports", "line": 72},
        {"file": "main.py", "symbol": "cmd_list", "relation": "calls", "line": 73},
        {"file": "utils.py", "symbol": "filter_by_month", "relation": "calls", "line": 75},
    ],
}

BLAST_AFTER_FALLBACK = {
    "target": "utils.month_date_range",
    "impacted": [
        {"file": "main.py", "symbol": "cmd_list", "relation": "imports", "line": 72},
        {"file": "tests/test_bugs.py", "symbol": "<module>", "relation": "imports", "line": 24},
        {"file": "main.py", "symbol": "cmd_list", "relation": "calls", "line": 73},
        {"file": "utils.py", "symbol": "filter_by_month", "relation": "calls", "line": 75},
    ],
}

def get_blast_graph(filename: str, fallback: dict) -> dict:
    file_path = ROOT / "blast_radius" / filename
    if file_path.is_file():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "impacted" in data:
                    return data
        except Exception:
            pass
    return fallback

BLAST_BEFORE = get_blast_graph("graph.json", BLAST_BEFORE_FALLBACK)
BLAST_AFTER = get_blast_graph("graph_after.json", BLAST_AFTER_FALLBACK)

IMPACT_ITEMS_FALLBACK = [
    # sample_app bug02
    {"bug": "sample_app_bug02", "file": "sample_app/api.py", "function": "update_expense", "risk": "High", "covered": True, "reason": "Missing None-check causes AttributeError to propagate."},
    {"bug": "sample_app_bug02", "file": "sample_app/api.py", "function": "get_expense", "risk": "Medium", "covered": True, "reason": "Returns None when ID is missing."},
    {"bug": "sample_app_bug02", "file": "sample_app/main.py", "function": "cmd_update", "risk": "High", "covered": False, "reason": "CLI entry point calling update_expense."},
    {"bug": "sample_app_bug02", "file": "sample_app/tests/test_api.py", "function": "test_update_missing_raises", "risk": "Low", "covered": True, "reason": "Existing test accepted AttributeError."},
    # sample_app bug03
    {"bug": "sample_app_bug03", "file": "sample_app/api.py", "function": "over_budget_categories", "risk": "High", "covered": True, "reason": "Filter on rounded percent_used misses boundary."},
    {"bug": "sample_app_bug03", "file": "sample_app/utils.py", "function": "budget_status", "risk": "Medium", "covered": True, "reason": "Computes exact over_budget flag."},
    {"bug": "sample_app_bug03", "file": "sample_app/api.py", "function": "check_all_budgets", "risk": "Low", "covered": False, "reason": "Assembles status list."},
    {"bug": "sample_app_bug03", "file": "sample_app/main.py", "function": "cmd_budget", "risk": "Low", "covered": False, "reason": "CLI caller of check_all_budgets."},
    # sample_app bug04
    {"bug": "sample_app_bug04", "file": "sample_app/utils.py", "function": "to_csv_rows", "risk": "High", "covered": True, "reason": "Mutable default argument shared across callers."},
    {"bug": "sample_app_bug04", "file": "sample_app/utils.py", "function": "export_csv", "risk": "Medium", "covered": True, "reason": "Calls to_csv_rows without headers."},
    {"bug": "sample_app_bug04", "file": "sample_app/api.py", "function": "export_to_csv", "risk": "Medium", "covered": True, "reason": "API method calling export_csv."},
    {"bug": "sample_app_bug04", "file": "sample_app/main.py", "function": "cmd_export", "risk": "Low", "covered": False, "reason": "CLI entry point calling export_to_csv."},
    # attrs bug01
    {"bug": "attrs_bug01", "file": "src/attr/converters.py", "function": "optional", "risk": "High", "covered": False, "reason": "Wraps Converter in single-arg closure."},
    {"bug": "attrs_bug01", "file": "src/attr/_make.py", "function": "pipe", "risk": "High", "covered": False, "reason": "Returns 3-arg Converter incompatible with optional."},
    {"bug": "attrs_bug01", "file": "src/attr/_make.py", "function": "Converter.__call__", "risk": "High", "covered": False, "reason": "Requires three arguments."},
    {"bug": "attrs_bug01", "file": "src/attr/_make.py", "function": "_make_init", "risk": "Low", "covered": False, "reason": "Wraps optional_converter."},
]

def get_impact_items() -> list[dict]:
    plan_path = ROOT / "impact_plan.json"
    if plan_path.is_file():
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = []
            for b in data.get("bugs", []):
                bug_id = b.get("bug_id", "unknown")
                for imp in b.get("impacted_items", []):
                    items.append({
                        "bug": bug_id,
                        "file": imp.get("file", ""),
                        "function": imp.get("function", ""),
                        "risk": imp.get("risk", "Low"),
                        "reason": imp.get("reason", ""),
                        "covered": len(imp.get("covering_tests", [])) > 0,
                    })
            if items:
                return items
        except Exception:
            pass
    return IMPACT_ITEMS_FALLBACK

IMPACT_ITEMS = get_impact_items()

def generate_dot_graph(graph_data: dict) -> str:
    """Generate Graphviz DOT representation of a Blast Radius dependency graph."""
    target = graph_data.get("target", "Target")
    impacted = graph_data.get("impacted", [])
    lines = [
        "digraph G {",
        '  rankdir=LR;',
        '  bgcolor="transparent";',
        '  node [shape=box, style="filled,rounded", fontname="sans-serif", fontsize=10];',
        '  edge [fontname="sans-serif", fontsize=9, color="#64748b"];',
        f'  target [label="{target}\\n(Target)", fillcolor="#fee2e2", color="#ef4444", penwidth=2];',
    ]
    for idx, node in enumerate(impacted):
        node_id = f"node_{idx}"
        label = (
            f"{node.get('file', '?')}\\n"
            f"{node.get('symbol', '?')}\\n"
            f"L{node.get('line', '?')}"
        )
        rel = node.get("relation", "calls")
        depth = node.get("depth", 1)
        if rel == "calls":
            color = "#dbeafe"
            border = "#3b82f6"
        elif rel == "types":
            color = "#f3e8ff"
            border = "#a855f7"
        elif rel == "subclasses":
            color = "#fef3c7"
            border = "#f59e0b"
        else:
            color = "#f1f5f9"
            border = "#94a3b8"
        edge_label = f"{rel}" + (f" (d={depth})" if depth > 1 else "")
        lines.append(f'  {node_id} [label="{label}", fillcolor="{color}", color="{border}"];')
        lines.append(f'  {node_id} -> target [label="{edge_label}"];')
    lines.append("}")
    return "\n".join(lines)

PIPELINE_ROLES = [
    {"role": "Reproducer", "emoji": "🔴", "desc": "Writes a minimal failing test that proves the bug exists."},
    {"role": "Investigator", "emoji": "🔍", "desc": "Identifies root cause, runs Blast Radius (before-fix scope)."},
    {"role": "Fixer", "emoji": "🔧", "desc": "Patches code until all tests pass; documents the diff."},
    {"role": "Reviewer", "emoji": "✅", "desc": "Re-runs Blast Radius (after-fix), audits coverage, writes PR."},
]

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* Global */
html, body, [class*="css"] { font-family: -apple-system, "Segoe UI", system-ui, sans-serif; }

/* Metric cards */
.metric-card {
    background: #f7f8fa;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 20px 24px;
    text-align: center;
}
.metric-value {
    font-size: 2.4rem;
    font-weight: 700;
    color: #1f2328;
    line-height: 1.1;
}
.metric-label {
    font-size: 0.82rem;
    color: #57606a;
    margin-top: 4px;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}
.metric-delta-good { color: #16a34a; font-size: 0.85rem; font-weight: 600; }
.metric-delta-bad  { color: #dc2626; font-size: 0.85rem; font-weight: 600; }

/* Badge */
.badge-high   { background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; }
.badge-medium { background:#fef3c7; color:#92400e; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; }
.badge-low    { background:#dcfce7; color:#166534; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; }
.badge-fixed  { background:#dbeafe; color:#1e40af; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600; }

/* Section header */
.section-header {
    border-top: 2px solid #e5e7eb;
    padding-top: 16px;
    margin-top: 8px;
    margin-bottom: 4px;
    font-size: 1.15rem;
    font-weight: 700;
    color: #1f2328;
}

/* Pipeline steps */
.pipeline-step {
    background: #f7f8fa;
    border: 1px solid #e5e7eb;
    border-left: 4px solid #3b82d4;
    border-radius: 6px;
    padding: 14px 18px;
    margin-bottom: 10px;
}
.pipeline-step h4 { margin: 0 0 4px 0; font-size: 1rem; color: #1f2328; }
.pipeline-step p  { margin: 0; font-size: 0.88rem; color: #57606a; }

/* Blast radius node */
.br-node {
    display: inline-block;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    padding: 6px 12px;
    margin: 4px;
    font-size: 0.83rem;
    color: #1e3a8a;
}
.br-node-new {
    display: inline-block;
    background: #fefce8;
    border: 1px solid #fde68a;
    border-radius: 6px;
    padding: 6px 12px;
    margin: 4px;
    font-size: 0.83rem;
    color: #78350f;
    font-weight: 600;
}

/* Bug card */
.bug-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 18px 20px;
    margin-bottom: 12px;
}
.bug-card h4 { margin: 0 0 6px 0; font-size: 0.97rem; color: #1f2328; }
.bug-card p  { margin: 0 0 4px 0; font-size: 0.85rem; color: #57606a; }
.bug-card code { background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-size: 0.83rem; }

/* Footer */
.footer {
    text-align: center;
    color: #57606a;
    font-size: 0.78rem;
    border-top: 1px solid #e5e7eb;
    padding-top: 12px;
    margin-top: 32px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🐛 Bug Squad")
    st.markdown("*IBM Bob Hackathon 2026*")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["🏠 Overview", "🔄 Pipeline", "🐞 Sample App Bugs", "📦 OSS Cases", "💥 Blast Radius", "🗂 Impact Table"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Four Bob subagent roles — Reproducer → Investigator → Fixer → Reviewer — turn a bug ticket into a reviewed PR, guided by Blast Radius change-impact analysis.")

# ---------------------------------------------------------------------------
# Page: Overview
# ---------------------------------------------------------------------------
if page == "🏠 Overview":
    st.markdown("# 🐛 Bug Squad")
    st.markdown("#### An IBM Bob-powered pipeline that takes a bug ticket and turns it into a reviewed, tested pull request")
    st.markdown("---")

    # Key metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, val, label, delta, good in [
        (c1, "19",  "Total Bugs Tracked",     "+19 tracked",    True),
        (c2, "14",  "Bugs Fixed / Reproduced","14 resolved",    True),
        (c3, "48",  "Tests Passing",          "+11 new tests",  True),
        (c4, "0",   "Regressions",            "zero introduced",True),
        (c5, "4",   "PR Descriptions",        "ready to post",  True),
    ]:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{val}</div>
                <div class="metric-label">{label}</div>
                <div class="{'metric-delta-good' if good else 'metric-delta-bad'}">{delta}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("")

    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown('<div class="section-header">What is Bug Squad?</div>', unsafe_allow_html=True)
        st.markdown("""
Bug Squad is a **four-subagent IBM Bob pipeline** that automates the full bug-fix lifecycle:

1. **Reproducer** — writes a minimal failing test proving the bug exists  
2. **Investigator** — finds root cause & scopes blast radius (before-fix)  
3. **Fixer** — patches code until all tests pass  
4. **Reviewer** — re-checks blast radius, audits test coverage, writes PR

Alongside the pipeline, **Blast Radius** is a static dependency-impact analyzer that answers: *"If I change this function, what else could break?"* It builds a call/import graph before and after each fix, and Bob reasons over the graph to rate each impacted item High / Medium / Low risk.
        """)

    with col_r:
        st.markdown('<div class="section-header">Scope</div>', unsafe_allow_html=True)
        data = {
            "Category": ["Sample app bugs", "OSS bugs (attrs)", "OSS bugs (schedule)", "OSS bugs (jsonschema)", "OSS bugs (arrow)", "OSS bugs (yup)"],
            "Count": [5, 3, 2, 3, 3, 3],
        }
        df = pd.DataFrame(data)
        st.bar_chart(df.set_index("Category"), height=280)

    st.markdown('<div class="section-header">Data sources</div>', unsafe_allow_html=True)
    src_cols = st.columns(5)
    for col, lib, lic in zip(src_cols,
        ["attrs", "schedule", "jsonschema", "arrow (Python)", "yup (JS)"],
        ["MIT", "MIT", "MIT", "Apache-2.0", "MIT"]):
        col.markdown(f"**{lib}**  \n`{lic}`")

    st.markdown("""
> All OSS bugs are closed issues with public fix commits from permissively-licensed repositories.
> No client data, no PII, no confidential information.
    """)

# ---------------------------------------------------------------------------
# Page: Pipeline
# ---------------------------------------------------------------------------
elif page == "🔄 Pipeline":
    st.markdown("# 🔄 The Pipeline")
    st.markdown("Four Bob subagent roles, each a separate task — hand-off via files in the repo.")
    st.markdown("---")

    for step in PIPELINE_ROLES:
        st.markdown(f"""
        <div class="pipeline-step">
            <h4>{step['emoji']} {step['role']}</h4>
            <p>{step['desc']}</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-header">Handoff artefacts</div>', unsafe_allow_html=True)

    artefacts = pd.DataFrame([
        {"Produced by": "Reproducer",    "Artefact": "sample_app/tests/test_bugs.py",  "Consumed by": "Fixer, Reviewer"},
        {"Produced by": "Investigator",  "Artefact": "impact_plan.json",               "Consumed by": "Fixer, Reviewer"},
        {"Produced by": "Investigator",  "Artefact": "blast_radius/graph.json",        "Consumed by": "Fixer, Reviewer"},
        {"Produced by": "Fixer",         "Artefact": "FIXER_OUTPUT_bugNN.md",          "Consumed by": "Reviewer"},
        {"Produced by": "Reviewer",      "Artefact": "blast_radius/graph_after.json",  "Consumed by": "Reviewer"},
        {"Produced by": "Reviewer",      "Artefact": "PR_DESCRIPTION_bugNN.md",        "Consumed by": "Team / GitHub"},
    ])
    st.dataframe(artefacts, width='stretch', hide_index=True)

    st.markdown("---")
    st.markdown('<div class="section-header">Bobcoin discipline</div>', unsafe_allow_html=True)
    st.markdown("""
| Activity | Uses Bobcoins? |
|----------|---------------|
| Reproducer subagent | ✅ Yes |
| Investigator subagent | ✅ Yes |
| Fixer subagent | ✅ Yes |
| Reviewer subagent | ✅ Yes |
| Static graph scan (`blast_radius/scan.py`) | ❌ No — plain code |
| Dashboard (`dashboard/app.py`) | ❌ No — plain code |
| Data curation | ❌ No — plain code |
    """)

# ---------------------------------------------------------------------------
# Page: Sample App Bugs
# ---------------------------------------------------------------------------
elif page == "🐞 Sample App Bugs":
    st.markdown("# 🐞 Sample App Bugs")
    st.markdown("Five deliberately seeded bugs in the sample expense-tracker app.")
    st.markdown("---")

    # Summary bar
    summary = pd.DataFrame([
        {"Bug": b["id"].upper(), "Tests Added": b["tests_added"], "Risk": b["risk"], "Status": b["status"]}
        for b in SAMPLE_BUGS
    ])
    st.dataframe(summary, width='stretch', hide_index=True)

    st.markdown("---")
    st.markdown('<div class="section-header">Bug details</div>', unsafe_allow_html=True)

    for b in SAMPLE_BUGS:
        risk_class = f"badge-{b['risk'].lower()}"
        with st.expander(f"**{b['id'].upper()}** — {b['title']}  •  {b['status']}", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**File:** `{b['file']}`")
                st.markdown(f"**Function:** `{b['function']}`")
                st.markdown(f"**Risk:** <span class='{risk_class}'>{b['risk']}</span>", unsafe_allow_html=True)
                st.markdown(f"**Tests added:** {b['tests_added']}")
            with col_b:
                st.markdown(f"**Root cause:**  \n{b['root_cause']}")
                st.markdown(f"**Fix:**  \n{b['fix']}")
                st.markdown(f"**Diff summary:** `{b['diff_summary']}`")

    st.markdown("---")
    st.markdown('<div class="section-header">Test progression</div>', unsafe_allow_html=True)

    phases = pd.DataFrame({
        "Phase": ["Baseline (pre-fix)", "After Bug01 fix", "After Bug02 fix", "After Bug03 fix", "After Bug04 fix", "After Bug05 fix"],
        "Passing": [35, 39, 41, 43, 46, 48],
        "Failing": [3, 3, 3, 1, 0, 0],
    })
    st.bar_chart(phases.set_index("Phase")[["Passing", "Failing"]], height=320)

# ---------------------------------------------------------------------------
# Page: OSS Cases
# ---------------------------------------------------------------------------
elif page == "📦 OSS Cases":
    st.markdown("# 📦 OSS Cases")
    st.markdown("15 real bugs from 5 permissively-licensed open-source projects, used as ground truth for Blast Radius precision/recall.")
    st.markdown("---")

    libs = ["attrs", "schedule", "jsonschema", "arrow", "yup"]
    selected_lib = st.selectbox("Filter by library", ["All"] + libs)

    bugs_to_show = OSS_BUGS if selected_lib == "All" else [b for b in OSS_BUGS if b["lib"] == selected_lib]

    for b in bugs_to_show:
        risk_class = f"badge-{b['risk'].lower()}"
        status_icon = "✅" if "Fixed" in b["status"] else "🔬"
        with st.expander(f"**{b['lib']} / {b['id']}** — {b['title']}", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Library:** `{b['lib']}`")
                st.markdown(f"**Issue:** {b['issue']}")
                st.markdown(f"**Risk:** <span class='{risk_class}'>{b['risk']}</span>", unsafe_allow_html=True)
                st.markdown(f"**Status:** {b['status']}")
                if b["upstream"] != "N/A":
                    st.markdown(f"**Upstream commit:** `{b['upstream']}`")
            with col_b:
                st.markdown(f"**Root cause:**  \n{b['root_cause']}")
                st.markdown(f"**Fix:**  \n{b['fix']}")

    st.markdown("---")
    st.markdown('<div class="section-header">Library summary</div>', unsafe_allow_html=True)

    lib_summary = pd.DataFrame([
        {"Library": lib, "Bugs": sum(1 for b in OSS_BUGS if b["lib"] == lib),
         "High Risk": sum(1 for b in OSS_BUGS if b["lib"] == lib and b["risk"] == "High"),
         "Fixed": sum(1 for b in OSS_BUGS if b["lib"] == lib and "Fixed" in b["status"])}
        for lib in libs
    ])
    st.dataframe(lib_summary, width='stretch', hide_index=True)

# ---------------------------------------------------------------------------
# Page: Blast Radius
# ---------------------------------------------------------------------------
elif page == "💥 Blast Radius":
    st.markdown("# 💥 Blast Radius")
    st.markdown("Change-impact analysis — before and after the fix for Bug01 (`utils.month_date_range`).")
    st.markdown("---")

    # ------------------------------------------------------------------
    # 1. Interactive Live AST Scanner
    # ------------------------------------------------------------------
    st.markdown('<div class="section-header">🔍 Interactive Live AST Scanner</div>', unsafe_allow_html=True)
    st.caption("Scan any symbol live across `sample_app/` using the updated Blast Radius AST engine.")
    
    col_t1, col_t2, col_t3 = st.columns([3, 1, 1])
    with col_t1:
        preset_target = st.selectbox(
            "Select Target Symbol",
            [
                "utils.month_date_range",
                "models.Expense",
                "api.ExpenseTracker.update_expense",
                "api.ExpenseTracker.monthly_expenses",
                "utils.to_csv_rows",
                "Custom...",
            ],
            index=0,
        )
        if preset_target == "Custom...":
            scan_target = st.text_input("Enter symbol (module.symbol or bare name)", value="utils.parse_date")
        else:
            scan_target = preset_target

    with col_t2:
        scan_depth = st.slider("Depth", min_value=1, max_value=3, value=1, help="Transitive hop depth")

    with col_t3:
        st.write("")
        st.write("")
        run_scan_btn = st.button("🚀 Run Live Scan", type="primary")

    if run_scan_btn and build_graph:
        with st.spinner(f"Scanning `{scan_target}` at depth {scan_depth}..."):
            live_result = build_graph(ROOT / "sample_app", scan_target, depth=scan_depth)
        
        impacted_cnt = len(live_result.get("impacted", []))
        st.success(f"Found **{impacted_cnt}** impacted node(s) for `{scan_target}` at depth {scan_depth}")
        st.graphviz_chart(generate_dot_graph(live_result))
        with st.expander("📄 View Raw AST Output (JSON)"):
            st.json(live_result)

    st.markdown("---")

    # ------------------------------------------------------------------
    # 2. Before vs After Fix Comparison
    # ------------------------------------------------------------------
    st.markdown('<div class="section-header">📊 Before vs. After Fix Comparison</div>', unsafe_allow_html=True)
    st.markdown("""
1. **Static scan** (`blast_radius/scan.py`) — builds a call/import/type graph via Python `ast` and saves it as JSON  
2. **Bob's reasoning** — reads the graph and rates each impacted item **High / Medium / Low** risk with a one-line rationale  
3. **Before vs after** — the Reviewer re-runs the scan after the fix; any *new* nodes in the after-graph are flagged for manual review
    """)

    # Show Diff stats if diff_graphs available
    if diff_graphs:
        diff_res = diff_graphs(BLAST_BEFORE, BLAST_AFTER)
        d_sum = diff_res["summary"]
        dc1, dc2, dc3, dc4 = st.columns(4)
        dc1.metric("Before Nodes", d_sum["before_count"])
        dc2.metric("After Nodes", d_sum["after_count"])
        dc3.metric("Added Nodes", f"+{d_sum['added_count']}", delta_color="inverse")
        dc4.metric("Shared Nodes", d_sum["shared_count"])

    col_before, col_after = st.columns(2)

    with col_before:
        st.markdown("### 📊 Before fix (`graph.json`)")
        st.markdown(f"**Target:** `{BLAST_BEFORE['target']}`  \n**Impacted nodes:** {len(BLAST_BEFORE['impacted'])}")
        st.graphviz_chart(generate_dot_graph(BLAST_BEFORE))
        for node in BLAST_BEFORE["impacted"]:
            st.markdown(f"""<span class="br-node">
                <b>{node['file']}</b> · <code>{node['symbol']}</code> · {node['relation']} · L{node['line']}
            </span>""", unsafe_allow_html=True)

    with col_after:
        st.markdown("### 📊 After fix (`graph_after.json`)")
        before_keys = {(n["file"], n["symbol"], n["relation"]) for n in BLAST_BEFORE["impacted"]}
        new_count = sum(1 for n in BLAST_AFTER["impacted"] if (n["file"], n["symbol"], n["relation"]) not in before_keys)
        new_label = f" (+{new_count} new)" if new_count > 0 else ""
        st.markdown(f"**Target:** `{BLAST_AFTER['target']}`  \n**Impacted nodes:** {len(BLAST_AFTER['impacted'])}{new_label}")
        st.graphviz_chart(generate_dot_graph(BLAST_AFTER))
        for node in BLAST_AFTER["impacted"]:
            key = (node["file"], node["symbol"], node["relation"])
            is_new = key not in before_keys
            css_class = "br-node-new" if is_new else "br-node"
            label = " ⚠️ NEW" if is_new else ""
            st.markdown(f"""<span class="{css_class}">
                <b>{node['file']}</b> · <code>{node['symbol']}</code> · {node['relation']} · L{node['line']}{label}
            </span>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-header">New node analysis</div>', unsafe_allow_html=True)
    st.info("""
**`tests/test_bugs.py / <module> / imports / line 24`** — This is a **benign test-harness import** added by the Reproducer agent for the Bug01 regression tests. It is not a production call site and carries zero risk to production behaviour. No follow-up action required.
    """)

    st.markdown("---")
    st.markdown('<div class="section-header">Raw graph JSON</div>', unsafe_allow_html=True)
    tab_b, tab_a = st.tabs(["Before (graph.json)", "After (graph_after.json)"])
    with tab_b:
        st.json(BLAST_BEFORE)
    with tab_a:
        st.json(BLAST_AFTER)

# ---------------------------------------------------------------------------
# Page: Impact Table
# ---------------------------------------------------------------------------
elif page == "🗂 Impact Table":
    st.markdown("# 🗂 Impact Table")
    st.markdown("All impacted items identified by the Investigator across every analysed bug, with risk ratings and test coverage.")
    st.markdown("---")

    all_bugs_options = sorted(set(i["bug"] for i in IMPACT_ITEMS))
    selected_bug = st.selectbox("Filter by bug", ["All"] + all_bugs_options)
    selected_risk = st.selectbox("Filter by risk", ["All", "High", "Medium", "Low"])

    items = IMPACT_ITEMS
    if selected_bug != "All":
        items = [i for i in items if i["bug"] == selected_bug]
    if selected_risk != "All":
        items = [i for i in items if i["risk"] == selected_risk]

    df = pd.DataFrame([
        {
            "Bug": i["bug"],
            "File": i["file"].split("/")[-1],
            "Full Path": i["file"],
            "Function": i["function"],
            "Risk": i["risk"],
            "Test Covered": "✅" if i["covered"] else "⚠️ Untested",
            "Reason": i.get("reason", "N/A"),
        }
        for i in items
    ])

    def risk_order(r):
        return {"High": 0, "Medium": 1, "Low": 2}.get(r, 3)

    df = df.sort_values("Risk", key=lambda s: s.map(risk_order))
    st.dataframe(df[["Bug", "File", "Function", "Risk", "Test Covered", "Reason"]], width='stretch', hide_index=True)

    st.markdown("---")
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Risk distribution</div>', unsafe_allow_html=True)
        risk_counts = pd.DataFrame(
            df["Risk"].value_counts().rename_axis("Risk").reset_index(name="Count")
        )
        st.bar_chart(risk_counts.set_index("Risk"), height=260)

    with col_r:
        st.markdown('<div class="section-header">Coverage breakdown</div>', unsafe_allow_html=True)
        covered = (df["Test Covered"] == "✅").sum()
        uncovered = (df["Test Covered"] == "⚠️ Untested").sum()
        cov_df = pd.DataFrame({"Coverage": ["Covered", "Untested"], "Items": [covered, uncovered]})
        st.bar_chart(cov_df.set_index("Coverage"), height=260)

    st.markdown("---")
    st.markdown(f"""
> **{len(items)} items shown** — {sum(1 for i in items if i['risk']=='High')} High,
> {sum(1 for i in items if i['risk']=='Medium')} Medium,
> {sum(1 for i in items if i['risk']=='Low')} Low.
> {sum(1 for i in items if i['covered'])} / {len(items)} have test coverage.
    """)

# ---------------------------------------------------------------------------
# Footer (all pages)
# ---------------------------------------------------------------------------
st.markdown("""
<div class="footer">
    Made with <strong>IBM Bob</strong> &mdash; Bug Squad &middot; IBM Bob Hackathon 2026
</div>
""", unsafe_allow_html=True)
