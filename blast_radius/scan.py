#!/usr/bin/env python3
"""
blast_radius/scan.py — Static call/dependency graph builder & impact analyzer.

Walks every Python file under REPO_PATH, parses each one with the `ast`
module, and records relationships to the TARGET symbol:

  calls       – a function/method body contains a call to the target name
  imports     – a file imports the target name (or the module that owns it)
  subclasses  – a class lists the target as one of its bases
  types       – a function signature or variable uses the target as a type annotation

Supports transitive multi-hop blast radius scanning via `--depth <N>`,
and before/after graph comparison via `--diff <BEFORE> <AFTER>`.

Usage
-----
    # Standard direct scan (depth 1):
    python blast_radius/scan.py \\
        --repo   sample_app \\
        --target utils.month_date_range \\
        --out    blast_radius/graph.json

    # Transitive multi-hop scan (e.g. depth 2):
    python blast_radius/scan.py \\
        --repo   sample_app \\
        --target utils.month_date_range \\
        --depth  2

    # Compare before and after fix graphs:
    python blast_radius/scan.py \\
        --diff blast_radius/graph.json blast_radius/graph_after.json
"""

from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import sys
from typing import Dict, Iterator, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

class Impact:
    """One impacted item in the dependency graph."""

    __slots__ = ("file", "symbol", "relation", "line", "depth")

    def __init__(
        self,
        file: str,
        symbol: str,
        relation: str,
        line: int,
        depth: int = 1,
    ) -> None:
        self.file = file
        self.symbol = symbol
        self.relation = relation
        self.line = line
        self.depth = depth

    def to_dict(self) -> Dict[str, object]:
        data: Dict[str, object] = {
            "file": self.file,
            "symbol": self.symbol,
            "relation": self.relation,
            "line": self.line,
        }
        if self.depth > 1:
            data["depth"] = self.depth
        return data


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _iter_python_files(repo: Path) -> Iterator[Path]:
    """Yield every .py file under *repo*, skipping hidden dirs and virtualenvs."""
    for root, dirs, files in os.walk(repo):
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d not in (
                "__pycache__", ".git", ".tox", "node_modules",
                ".venv", "venv", "env", "dist", "build"
            )
        ]
        for fname in files:
            if fname.endswith(".py"):
                yield Path(root) / fname


def _parse_file(path: Path) -> Optional[ast.Module]:
    """Parse *path* and return the AST, or None on syntax error."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        return ast.parse(source, filename=str(path))
    except SyntaxError:
        return None


def _qualified_name(node: ast.expr) -> Optional[str]:
    """
    Resolve an AST expression to a dotted name string, e.g.
      ast.Name      → "foo"
      ast.Attribute → "obj.method"
    Returns None for anything more complex (subscripts, calls, etc.).
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value)
        if parent is not None:
            return f"{parent}.{node.attr}"
    return None


# ---------------------------------------------------------------------------
# Enclosing-symbol tracker — thin wrapper over NodeVisitor
# ---------------------------------------------------------------------------

class _SymbolStack:
    """
    Maintains a stack of enclosing definition names (module → class → function)
    as we walk an AST.
    """

    def __init__(self) -> None:
        self._stack: List[str] = []

    def push(self, name: str) -> None:
        self._stack.append(name)

    def pop(self) -> None:
        self._stack.pop()

    def current(self) -> str:
        """Return the current fully-qualified symbol name, e.g. 'ClassName.method'."""
        return ".".join(self._stack) if self._stack else "<module>"


# ---------------------------------------------------------------------------
# Main visitor
# ---------------------------------------------------------------------------

class _GraphVisitor(ast.NodeVisitor):
    """
    Walk one file's AST and emit Impact records for every occurrence of the
    target symbol.
    """

    def __init__(
        self,
        target_module: Optional[str],
        target_name: str,
        rel_path: str,
        depth: int = 1,
    ) -> None:
        self._target_module = target_module
        self._target_name = target_name
        self._rel_path = rel_path
        self._depth = depth
        self._stack = _SymbolStack()
        self.impacts: List[Impact] = []

        # Track what local aliases the target_name/target_module were imported as
        # key: local alias, value: original qualified name
        self._aliases: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Scope tracking & Type annotations
    # ------------------------------------------------------------------

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._stack.push(node.name)
        # Check whether this class subclasses the target
        for base in node.bases:
            base_name = _qualified_name(base)
            if base_name and self._matches_name(base_name):
                self.impacts.append(Impact(
                    file=self._rel_path,
                    symbol=self._stack.current(),
                    relation="subclasses",
                    line=node.lineno,
                    depth=self._depth,
                ))
        self.generic_visit(node)
        self._stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._stack.push(node.name)

        # Check argument type annotations
        all_args = (
            getattr(node.args, "posonlyargs", [])
            + node.args.args
            + node.args.kwonlyargs
        )
        for arg in all_args:
            if arg.annotation:
                line = getattr(arg, "lineno", node.lineno)
                self._check_annotation(arg.annotation, line)

        if node.args.vararg and node.args.vararg.annotation:
            self._check_annotation(node.args.vararg.annotation, node.lineno)
        if node.args.kwarg and node.args.kwarg.annotation:
            self._check_annotation(node.args.kwarg.annotation, node.lineno)
        if node.returns:
            self._check_annotation(node.returns, node.lineno)

        self.generic_visit(node)
        self._stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Handle:  variable: TargetType = ..."""
        if node.annotation:
            self._check_annotation(node.annotation, node.lineno)
        self.generic_visit(node)

    def _check_annotation(self, node: Optional[ast.AST], lineno: int) -> None:
        """Check if an annotation AST contains references to the target."""
        if node is None:
            return
        for subnode in ast.walk(node):
            if isinstance(subnode, (ast.Name, ast.Attribute)):
                name = _qualified_name(subnode)
                if name and self._matches_name(name):
                    self.impacts.append(Impact(
                        file=self._rel_path,
                        symbol=self._stack.current(),
                        relation="types",
                        line=lineno,
                        depth=self._depth,
                    ))
                    break

    # ------------------------------------------------------------------
    # Import tracking
    # ------------------------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:
        """Handle:  import utils  /  import utils as u"""
        for alias in node.names:
            mod = alias.name
            local = alias.asname or alias.name

            # Direct module import: `import utils`
            if self._target_module and mod == self._target_module:
                self.impacts.append(Impact(
                    file=self._rel_path,
                    symbol=self._stack.current(),
                    relation="imports",
                    line=node.lineno,
                    depth=self._depth,
                ))
                self._aliases[local] = mod

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle:  from utils import month_date_range [as x]"""
        mod = node.module or ""
        for alias in node.names:
            imported_name = alias.name
            local_name = alias.asname or alias.name

            target_mod_matches = (
                self._target_module is None or mod == self._target_module
            )
            if target_mod_matches and imported_name == self._target_name:
                self.impacts.append(Impact(
                    file=self._rel_path,
                    symbol=self._stack.current(),
                    relation="imports",
                    line=node.lineno,
                    depth=self._depth,
                ))
                self._aliases[local_name] = f"{mod}.{imported_name}"

            if imported_name == "*" and self._target_module and mod == self._target_module:
                self.impacts.append(Impact(
                    file=self._rel_path,
                    symbol=self._stack.current(),
                    relation="imports",
                    line=node.lineno,
                    depth=self._depth,
                ))

        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Call tracking
    # ------------------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        called = _qualified_name(node.func)
        if called and self._matches_call(called):
            self.impacts.append(Impact(
                file=self._rel_path,
                symbol=self._stack.current(),
                relation="calls",
                line=node.lineno,
                depth=self._depth,
            ))
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Match helpers
    # ------------------------------------------------------------------

    def _matches_name(self, name: str) -> bool:
        """
        True if *name* refers to the target symbol.
        """
        if name == self._target_name:
            return True
        if self._target_module and name == f"{self._target_module}.{self._target_name}":
            return True

        parts = name.split(".", 1)
        alias_root = parts[0]
        alias_attr = parts[1] if len(parts) > 1 else None

        if alias_root in self._aliases:
            resolved = self._aliases[alias_root]
            if alias_attr is None:
                expected = (
                    f"{self._target_module}.{self._target_name}"
                    if self._target_module else self._target_name
                )
                return resolved == expected
            return alias_attr == self._target_name

        return False

    def _matches_call(self, called: str) -> bool:
        """Match direct calls or method invocations with receiver validation."""
        if self._matches_name(called):
            return True

        parts = called.rsplit(".", 1)
        if len(parts) == 2 and parts[1] == self._target_name:
            if self._target_module:
                receiver = parts[0]
                if receiver in ("self", "cls"):
                    return True
                if receiver in self._aliases and self._aliases[receiver] == self._target_module:
                    return True
                if receiver == self._target_module:
                    return True
                return False
            return True
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _scan_single_target(
    repo: Path,
    target_module: Optional[str],
    target_name: str,
    depth: int = 1,
) -> List[Impact]:
    """Scan all Python files in *repo* for references to a single symbol."""
    impacts: List[Impact] = []
    for py_file in _iter_python_files(repo):
        tree = _parse_file(py_file)
        if tree is None:
            continue

        try:
            rel = py_file.relative_to(repo)
        except ValueError:
            rel = py_file

        visitor = _GraphVisitor(
            target_module=target_module,
            target_name=target_name,
            rel_path=str(rel),
            depth=depth,
        )
        visitor.visit(tree)
        impacts.extend(visitor.impacts)

    return impacts


def build_graph(
    repo_path: str | Path,
    target: str,
    depth: int = 1,
) -> Dict[str, object]:
    """
    Scan all Python files under *repo_path* for references to *target*.

    Parameters
    ----------
    repo_path : path-like
        Root directory to scan.
    target : str
        Either ``"module.symbol"`` or bare ``"symbol"``.
    depth : int
        Maximum depth for transitive impact analysis (default: 1).

    Returns
    -------
    dict matching the documented graph.json schema.
    """
    repo = Path(repo_path).resolve()

    if "." in target:
        initial_module, initial_name = target.rsplit(".", 1)
    else:
        initial_module = None
        initial_name = target

    all_impacts: List[Impact] = []
    seen: Set[Tuple[str, str, str, int]] = set()

    current_targets: Set[Tuple[Optional[str], str]] = {(initial_module, initial_name)}
    visited_targets: Set[Tuple[Optional[str], str]] = set()

    for current_depth in range(1, max(1, depth) + 1):
        next_targets: Set[Tuple[Optional[str], str]] = set()

        for t_mod, t_name in current_targets:
            visited_targets.add((t_mod, t_name))
            level_impacts = _scan_single_target(repo, t_mod, t_name, depth=current_depth)

            for imp in level_impacts:
                key = (imp.file, imp.symbol, imp.relation, imp.line)
                if key not in seen:
                    seen.add(key)
                    all_impacts.append(imp)

                    # Expand transitive targets for deeper depth
                    if (
                        current_depth < depth
                        and imp.relation in ("calls", "subclasses")
                        and imp.symbol != "<module>"
                    ):
                        mod = Path(imp.file).stem
                        sym = imp.symbol
                        if "." in sym:
                            cls_name, m_name = sym.rsplit(".", 1)
                            next_targets.add((cls_name, m_name))
                            next_targets.add((mod, m_name))
                        else:
                            next_targets.add((mod, sym))
                            next_targets.add((None, sym))

        current_targets = next_targets - visited_targets
        if not current_targets:
            break

    # Sort: depth first, then relation (imports -> subclasses -> types -> calls), then file+line
    order = {"imports": 0, "subclasses": 1, "types": 2, "calls": 3}
    all_impacts.sort(key=lambda i: (i.depth, order.get(i.relation, 9), i.file, i.line))

    return {
        "target": target,
        "impacted": [i.to_dict() for i in all_impacts],
    }


def diff_graphs(before_graph: Dict[str, object], after_graph: Dict[str, object]) -> Dict[str, object]:
    """
    Compare before and after dependency graphs to highlight changes.

    Returns a structured dictionary with 'added', 'removed', and 'shared' impacts.
    """
    before_impacts: List[Dict[str, object]] = list(before_graph.get("impacted", []))  # type: ignore
    after_impacts: List[Dict[str, object]] = list(after_graph.get("impacted", []))    # type: ignore

    def make_key(item: Dict[str, object]) -> Tuple[str, str, str]:
        return (str(item.get("file")), str(item.get("symbol")), str(item.get("relation")))

    before_map = {make_key(i): i for i in before_impacts}
    after_map = {make_key(i): i for i in after_impacts}

    before_keys = set(before_map.keys())
    after_keys = set(after_map.keys())

    added = [after_map[k] for k in sorted(after_keys - before_keys)]
    removed = [before_map[k] for k in sorted(before_keys - after_keys)]
    shared = [after_map[k] for k in sorted(after_keys & before_keys)]

    return {
        "target": after_graph.get("target") or before_graph.get("target", "unknown"),
        "summary": {
            "before_count": len(before_impacts),
            "after_count": len(after_impacts),
            "added_count": len(added),
            "removed_count": len(removed),
            "shared_count": len(shared),
        },
        "added": added,
        "removed": removed,
        "shared": shared,
    }


def write_graph(graph: Dict[str, object], out_path: str | Path) -> None:
    """Serialize *graph* to *out_path* as pretty-printed JSON."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, indent=2)
    impacted_list = graph.get("impacted", [])
    count = len(impacted_list) if isinstance(impacted_list, list) else 0
    print(f"Wrote {count} impact(s) to {out}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build or compare call/dependency graphs for a target Python symbol.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        "--repo", metavar="PATH",
        help="Root directory of the repository to scan.",
    )
    p.add_argument(
        "--target", metavar="MODULE.SYMBOL",
        help=(
            "Fully- or partially-qualified target symbol.\n"
            "Examples:\n"
            "  utils.month_date_range\n"
            "  ExpenseTracker\n"
            "  models.Expense"
        ),
    )
    p.add_argument(
        "--depth", type=int, default=1, metavar="N",
        help="Max depth for transitive impact analysis (default: 1).",
    )
    p.add_argument(
        "--out", default=None, metavar="FILE",
        help="Output JSON file (default: blast_radius/graph.json for scan).",
    )
    p.add_argument(
        "--diff", nargs=2, metavar=("BEFORE_JSON", "AFTER_JSON"),
        help="Compare two graph JSON files and display impact deltas.",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Diff mode
    if args.diff:
        before_file, after_file = args.diff
        if not Path(before_file).is_file():
            print(f"Error: before graph file '{before_file}' does not exist.", file=sys.stderr)
            return 1
        if not Path(after_file).is_file():
            print(f"Error: after graph file '{after_file}' does not exist.", file=sys.stderr)
            return 1

        with open(before_file, "r", encoding="utf-8") as fb:
            before_g = json.load(fb)
        with open(after_file, "r", encoding="utf-8") as fa:
            after_g = json.load(fa)

        diff = diff_graphs(before_g, after_g)
        summary = diff["summary"]

        print("=" * 79)
        print("Blast Radius Graph Comparison")
        print(f"Target: {diff['target']}")
        print(
            f"Before: {summary['before_count']} nodes | After: {summary['after_count']} nodes "
            f"(+{summary['added_count']}, -{summary['removed_count']}, ={summary['shared_count']})"
        )
        print("=" * 79)

        if diff["added"]:
            print("\n[+] Added Impact Nodes:")
            for node in diff["added"]:
                print(f"  • {node['file']}:{node['line']} [{node['relation']}] {node['symbol']}")

        if diff["removed"]:
            print("\n[-] Removed Impact Nodes:")
            for node in diff["removed"]:
                print(f"  • {node['file']}:{node['line']} [{node['relation']}] {node['symbol']}")

        if not diff["added"] and not diff["removed"]:
            print("\nNo node additions or removals detected between graphs.")

        if args.out:
            write_graph(diff, args.out)

        return 0

    # Scan mode
    if not args.repo or not args.target:
        parser.error("--repo and --target are required when not using --diff.")

    if not Path(args.repo).is_dir():
        print(f"Error: repo path '{args.repo}' is not a directory.", file=sys.stderr)
        return 1

    graph = build_graph(args.repo, args.target, depth=args.depth)
    out_path = args.out or "blast_radius/graph.json"
    write_graph(graph, out_path)

    # Also print JSON output to stdout
    print(json.dumps(graph, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
