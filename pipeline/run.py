#!/usr/bin/env python3
"""
pipeline/run.py — Bug Squad 4-Stage Pipeline Orchestrator & Audit CLI.

Orchestrates, verifies, and audits handoff artifacts between the four IBM Bob
subagent roles:
  1. Reproducer  ➔ sample_app/tests/test_bugs.py
  2. Investigator ➔ impact_plan.json, blast_radius/graph.json
  3. Fixer        ➔ FIXER_OUTPUT_bugXX.md
  4. Reviewer     ➔ blast_radius/graph_after.json, PR_DESCRIPTION_bugXX.md

In strict adherence to Bobcoin discipline, this orchestrator is plain Python
(0 Bobcoins) that verifies subagent outputs and runs Blast Radius scans.

Usage
-----
    # Show pipeline completion status across all tickets:
    python pipeline/run.py status
    python pipeline/run.py status --format json

    # Audit risk ratings and test coverage in impact_plan.json:
    python pipeline/run.py audit
    python pipeline/run.py audit --format json

    # Compare before-fix vs. after-fix Blast Radius dependency graphs:
    python pipeline/run.py diff
    python pipeline/run.py diff --format json

    # Verify all handoff artifacts for a specific ticket:
    python pipeline/run.py verify --bug bug02
    python pipeline/run.py verify --bug bug02 --format json
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# Ensure blast_radius is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "blast_radius"))

try:
    from scan import build_graph, diff_graphs, write_graph
except ImportError:
    build_graph = None
    diff_graphs = None
    write_graph = None


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class StageStatus:
    """Status of each handoff artifact for a bug ticket."""

    bug_id: str
    ticket_file: str
    reproducer_found: bool
    investigator_plan_found: bool
    blast_before_found: bool
    fixer_output_found: bool
    blast_after_found: bool
    reviewer_pr_found: bool

    def completion_pct(self) -> int:
        checks = [
            self.reproducer_found,
            self.investigator_plan_found,
            self.blast_before_found,
            self.fixer_output_found,
            self.blast_after_found,
            self.reviewer_pr_found,
        ]
        return int((sum(checks) / len(checks)) * 100)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bug_id": self.bug_id,
            "ticket_file": self.ticket_file,
            "reproducer_found": self.reproducer_found,
            "investigator_plan_found": self.investigator_plan_found,
            "blast_before_found": self.blast_before_found,
            "fixer_output_found": self.fixer_output_found,
            "blast_after_found": self.blast_after_found,
            "reviewer_pr_found": self.reviewer_pr_found,
            "completion_pct": self.completion_pct(),
        }


# ---------------------------------------------------------------------------
# Discovery & Verification Helpers
# ---------------------------------------------------------------------------

def _find_sample_app_bugs(repo_root: Path) -> List[StageStatus]:
    """Find all sample_app bug tickets and inspect handoff artifacts."""
    statuses: List[StageStatus] = []
    bugs_dir = repo_root / "bugs"
    if not bugs_dir.is_dir():
        return statuses

    ticket_files = sorted(bugs_dir.glob("ticket_*.md"))
    reproducer_file = repo_root / "sample_app" / "tests" / "test_bugs.py"
    reproducer_code = (
        reproducer_file.read_text(encoding="utf-8", errors="replace")
        if reproducer_file.is_file()
        else ""
    )

    impact_plan_file = repo_root / "impact_plan.json"
    impact_data: Dict[str, Any] = {}
    if impact_plan_file.is_file():
        try:
            impact_data = json.loads(impact_plan_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    planned_bug_ids = {
        b.get("bug_id", "") for b in impact_data.get("bugs", [])
    }

    graph_file = repo_root / "blast_radius" / "graph.json"
    graph_after_file = repo_root / "blast_radius" / "graph_after.json"

    for tf in ticket_files:
        match = re.search(r"ticket_(\d+)", tf.stem)
        if not match:
            continue
        num_str = match.group(1)
        bug_id = f"bug{num_str}"

        has_reproducer = f"TestBug{num_str}" in reproducer_code
        has_plan = (
            bug_id in planned_bug_ids or f"sample_app_{bug_id}" in planned_bug_ids
        )

        fixer_file = repo_root / f"FIXER_OUTPUT_{bug_id}.md"
        has_fixer = fixer_file.is_file()

        pr_file = repo_root / f"PR_DESCRIPTION_{bug_id}.md"
        has_pr = pr_file.is_file()

        statuses.append(StageStatus(
            bug_id=bug_id,
            ticket_file=str(tf.relative_to(repo_root)),
            reproducer_found=has_reproducer,
            investigator_plan_found=has_plan,
            blast_before_found=graph_file.is_file(),
            fixer_output_found=has_fixer,
            blast_after_found=graph_after_file.is_file(),
            reviewer_pr_found=has_pr,
        ))

    return statuses


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------

def cmd_status(repo_root: Path, args: argparse.Namespace) -> int:
    """Print the 4-subagent pipeline handoff status (human or JSON)."""
    statuses = _find_sample_app_bugs(repo_root)

    if getattr(args, "format", "human") == "json":
        data = {
            "bugs": [s.to_dict() for s in statuses],
            "summary": {
                "total_bugs": len(statuses),
                "fully_completed": sum(1 for s in statuses if s.completion_pct() == 100),
                "avg_completion_pct": round(
                    sum(s.completion_pct() for s in statuses) / max(1, len(statuses)), 1
                ),
            },
        }
        print(json.dumps(data, indent=2))
        return 0

    print("=" * 79)
    print("🐛 Bug Squad Pipeline — 4-Stage Subagent Handoff Status")
    print("=" * 79)
    print(
        f"{'Bug ID':<8} {'Reproducer':<12} {'Investigator':<14} "
        f"{'Fixer':<10} {'Reviewer':<10} {'Progress':<10}"
    )
    print("-" * 79)

    for s in statuses:
        rep_icon = "✅ Done" if s.reproducer_found else "❌ Missing"
        inv_icon = "✅ Done" if (s.investigator_plan_found and s.blast_before_found) else "⚠️ Partial"
        fix_icon = "✅ Done" if s.fixer_output_found else "❌ Pending"
        rev_icon = "✅ Done" if (s.reviewer_pr_found and s.blast_after_found) else "⚠️ Pending"
        pct = f"{s.completion_pct()}%"

        print(
            f"{s.bug_id:<8} {rep_icon:<12} {inv_icon:<14} "
            f"{fix_icon:<10} {rev_icon:<10} {pct:<10}"
        )

    print("=" * 79)
    print("Stage Legend:")
    print("  • Reproducer:   sample_app/tests/test_bugs.py (failing test)")
    print("  • Investigator: impact_plan.json & blast_radius/graph.json")
    print("  • Fixer:        FIXER_OUTPUT_bugXX.md")
    print("  • Reviewer:     blast_radius/graph_after.json & PR_DESCRIPTION_bugXX.md")
    return 0


def cmd_audit(repo_root: Path, args: argparse.Namespace) -> int:
    """Audit impact_plan.json for risk ratings and untested dependencies (human or JSON)."""
    plan_path = repo_root / "impact_plan.json"
    if not plan_path.is_file():
        print(f"Error: Impact plan '{plan_path}' not found.", file=sys.stderr)
        return 1

    try:
        data = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Error parsing {plan_path}: {exc}", file=sys.stderr)
        return 1

    bugs = data.get("bugs", [])
    total_items = 0
    high_count = 0
    med_count = 0
    low_count = 0
    covered_count = 0

    audit_bugs: List[Dict[str, Any]] = []
    for b in bugs:
        bug_id = b.get("bug_id", "unknown")
        items = b.get("impacted_items", [])
        parsed_items: List[Dict[str, Any]] = []

        for item in items:
            total_items += 1
            risk = item.get("risk", "Low")
            if risk == "High":
                high_count += 1
            elif risk == "Medium":
                med_count += 1
            else:
                low_count += 1

            cov = len(item.get("covering_tests", [])) > 0
            if cov:
                covered_count += 1

            parsed_items.append({
                "file": item.get("file", ""),
                "function": item.get("function", ""),
                "risk": risk,
                "covered": cov,
                "covering_tests": item.get("covering_tests", []),
                "reason": item.get("reason", ""),
            })

        audit_bugs.append({
            "bug_id": bug_id,
            "root_cause": b.get("root_cause", ""),
            "impacted_items": parsed_items,
        })

    audit_result = {
        "bugs": audit_bugs,
        "summary": {
            "total_items": total_items,
            "high_risk": high_count,
            "medium_risk": med_count,
            "low_risk": low_count,
            "covered_items": covered_count,
            "uncovered_items": total_items - covered_count,
            "coverage_pct": round((covered_count / max(1, total_items)) * 100, 1),
        },
    }

    if getattr(args, "format", "human") == "json":
        print(json.dumps(audit_result, indent=2))
        return 0

    print("=" * 79)
    print("🔍 Bug Squad Impact Plan Audit (IBM Bob Investigator Output)")
    print("=" * 79)

    for ab in audit_bugs:
        items = ab["impacted_items"]
        print(f"\n📦 Bug: {ab['bug_id']} ({len(items)} impacted items)")
        print(f"   Root Cause: {ab['root_cause'][:90]}...")
        print(f"   {'File':<25} {'Function':<25} {'Risk':<8} {'Covered':<10}")
        print("   " + "-" * 70)

        for item in items:
            cov_str = "✅ Yes" if item["covered"] else "⚠️ Untested"
            f_name = Path(item["file"]).name
            func = item["function"][:23]
            print(f"   {f_name:<25} {func:<25} {item['risk']:<8} {cov_str:<10}")

    print("\n" + "=" * 79)
    print(f"Summary: {total_items} items analyzed across {len(bugs)} bug tickets")
    print(
        f"Risk breakdown: {high_count} High, {med_count} Medium, {low_count} Low | "
        f"Test Coverage: {covered_count}/{total_items} ({(covered_count/max(1, total_items))*100:.1f}%)"
    )
    print("=" * 79)
    return 0


def cmd_diff(repo_root: Path, args: argparse.Namespace) -> int:
    """Compare before and after fix Blast Radius graphs (human or JSON)."""
    if diff_graphs is None:
        print("Error: blast_radius/scan.py diff_graphs function not available.", file=sys.stderr)
        return 1

    before_path = repo_root / "blast_radius" / "graph.json"
    after_path = repo_root / "blast_radius" / "graph_after.json"

    if not before_path.is_file():
        print(f"Error: {before_path} does not exist.", file=sys.stderr)
        return 1
    if not after_path.is_file():
        print(f"Error: {after_path} does not exist.", file=sys.stderr)
        return 1

    with open(before_path, "r", encoding="utf-8") as fb:
        before_g = json.load(fb)
    with open(after_path, "r", encoding="utf-8") as fa:
        after_g = json.load(fa)

    diff = diff_graphs(before_g, after_g)

    if getattr(args, "format", "human") == "json":
        print(json.dumps(diff, indent=2))
        return 0

    summary = diff["summary"]

    print("=" * 79)
    print("💥 Blast Radius Graph Delta (Reviewer Audit)")
    print(f"Target Symbol: {diff['target']}")
    print(
        f"Before Nodes: {summary['before_count']} | After Nodes: {summary['after_count']} "
        f"(+{summary['added_count']} added, -{summary['removed_count']} removed, ={summary['shared_count']} shared)"
    )
    print("=" * 79)

    if diff["added"]:
        print("\n[+] Added Nodes (New Call Sites / Importers):")
        for node in diff["added"]:
            print(f"  • {node['file']}:{node['line']} [{node['relation']}] {node['symbol']}")
    else:
        print("\nNo new nodes added to dependency graph.")

    if diff["removed"]:
        print("\n[-] Removed Nodes:")
        for node in diff["removed"]:
            print(f"  • {node['file']}:{node['line']} [{node['relation']}] {node['symbol']}")

    return 0


def cmd_verify(repo_root: Path, args: argparse.Namespace) -> int:
    """Verify handoff artifacts for a given bug ID (human or JSON)."""
    bug = args.bug.lower()
    if not bug.startswith("bug"):
        bug = f"bug{bug}"

    num_str = bug.replace("bug", "")
    ticket_file = repo_root / "bugs" / f"ticket_{int(num_str):02d}.md"
    reproducer_file = repo_root / "sample_app" / "tests" / "test_bugs.py"
    fixer_file = repo_root / f"FIXER_OUTPUT_{bug}.md"
    pr_file = repo_root / f"PR_DESCRIPTION_{bug}.md"
    plan_file = repo_root / "impact_plan.json"
    graph_file = repo_root / "blast_radius" / "graph.json"
    graph_after_file = repo_root / "blast_radius" / "graph_after.json"

    has_ticket = ticket_file.is_file()
    has_reproducer = (
        reproducer_file.is_file()
        and f"TestBug{int(num_str):02d}" in reproducer_file.read_text(encoding="utf-8")
    )
    has_plan = plan_file.is_file()
    has_fixer = fixer_file.is_file()
    has_pr = pr_file.is_file()
    has_graph_before = graph_file.is_file()
    has_graph_after = graph_after_file.is_file()

    all_ok = has_ticket and has_reproducer and has_plan and has_fixer and has_pr

    verify_result = {
        "bug_id": bug,
        "complete": all_ok,
        "artifacts": {
            "ticket": {
                "found": has_ticket,
                "file": str(ticket_file.relative_to(repo_root)) if has_ticket else None,
            },
            "reproducer": {
                "found": has_reproducer,
                "symbol": f"TestBug{int(num_str):02d}",
                "file": "sample_app/tests/test_bugs.py",
            },
            "investigator": {
                "found": has_plan,
                "file": "impact_plan.json",
                "graph_before": has_graph_before,
            },
            "fixer": {
                "found": has_fixer,
                "file": fixer_file.name if has_fixer else None,
            },
            "reviewer": {
                "found": has_pr,
                "file": pr_file.name if has_pr else None,
                "graph_after": has_graph_after,
            },
        },
    }

    if getattr(args, "format", "human") == "json":
        print(json.dumps(verify_result, indent=2))
        return 0 if all_ok else 1

    print("=" * 79)
    print(f"📋 Verifying Pipeline Handoff Artifacts for {bug.upper()}")
    print("=" * 79)

    # 1. Ticket
    if has_ticket:
        print(f"  [1] Ticket:        ✅ Found ({ticket_file.relative_to(repo_root)})")
    else:
        print(f"  [1] Ticket:        ❌ Missing ({ticket_file.relative_to(repo_root)})")

    # 2. Reproducer
    if has_reproducer:
        print(f"  [2] Reproducer:    ✅ Found TestBug{int(num_str):02d} in test_bugs.py")
    else:
        print(f"  [2] Reproducer:    ❌ TestBug{int(num_str):02d} not found in test_bugs.py")

    # 3. Investigator
    if has_plan:
        print(f"  [3] Investigator:  ✅ impact_plan.json verified")
    else:
        print(f"  [3] Investigator:  ❌ impact_plan.json missing")

    # 4. Fixer
    if has_fixer:
        print(f"  [4] Fixer Output:  ✅ Found ({fixer_file.name})")
    else:
        print(f"  [4] Fixer Output:  ⚠️ Missing ({fixer_file.name})")

    # 5. Reviewer PR
    if has_pr:
        print(f"  [5] Reviewer PR:   ✅ Found ({pr_file.name})")
    else:
        print(f"  [5] Reviewer PR:   ⚠️ Missing ({pr_file.name})")

    print("-" * 79)
    if all_ok:
        print(f"Status: Core pipeline handoff artifacts for {bug.upper()} are complete!")
        return 0
    else:
        print(f"Status: Some artifacts for {bug.upper()} are missing or incomplete.", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Main CLI Parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--format", choices=["human", "json"], default="human",
        help="Output format: 'human' (default) or 'json'.",
    )

    p = argparse.ArgumentParser(
        description="Bug Squad Pipeline Orchestrator and Artifact Audit CLI.",
        formatter_class=argparse.RawTextHelpFormatter,
        parents=[common],
    )
    sub = p.add_subparsers(dest="command", required=True)

    # status
    sub.add_parser(
        "status", parents=[common],
        help="Show 4-stage pipeline completion status across tickets",
    )

    # audit
    sub.add_parser(
        "audit", parents=[common],
        help="Audit risk ratings and test coverage in impact_plan.json",
    )

    # diff
    sub.add_parser(
        "diff", parents=[common],
        help="Compare before and after fix Blast Radius graphs",
    )

    # verify
    p_verify = sub.add_parser(
        "verify", parents=[common],
        help="Verify pipeline handoff artifacts for a specific bug",
    )
    p_verify.add_argument("--bug", required=True, help="Bug identifier (e.g. bug01, bug02, 03)")

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "status": cmd_status,
        "audit": cmd_audit,
        "diff": cmd_diff,
        "verify": cmd_verify,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(REPO_ROOT, args)


if __name__ == "__main__":
    sys.exit(main())
