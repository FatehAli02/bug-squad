#!/usr/bin/env python3
"""
blast_radius/scan.py — Static call/dependency graph builder.

Walks every Python file under REPO_PATH, parses each one with the `ast`
module, and records three kinds of relationship to the TARGET symbol:

  calls       – a function/method body contains a call to the target name
  imports     – a file imports the target name (or the module that owns it)
  subclasses  – a class lists the target as one of its bases

Usage
-----
    python blast_radius/scan.py \\
        --repo   /path/to/project \\
        --target utils.month_date_range \\
        --out    blast_radius/graph.json

    # or: target is just a bare name (no module prefix)
    python blast_radius/scan.py --repo sample_app --target month_date_range

Output (graph.json)
-------------------
    {
      "target": "utils.month_date_range",
      "impacted": [
        {"file": "api.py", "symbol": "ExpenseTracker.monthly_expenses",
         "relation": "calls", "line": 123},
        {"file": "utils.py", "symbol": "<module>",
         "relation": "imports", "line": 1},
        ...
      ]
    }
"""

from __future__ import annotations

import ast
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterator, List, Optional


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

class Impact:
    """One impacted item in the dependency graph."""

    __slots__ = ("file", "symbol", "relation", "line")

    def __init__(self, file: str, symbol: str, relation: str, line: int) -> None:
        self.file = file
        self.symbol = symbol
        self.relation = relation
        self.line = line

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "symbol": self.symbol,
            "relation": self.relation,
            "line": self.line,
        }


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _iter_python_files(repo: Path) -> Iterator[Path]:
    """Yield every .py file under *repo*, skipping hidden dirs and __pycache__."""
    for root, dirs, files in os.walk(repo):
        # Prune directories we never want to descend into
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d not in ("__pycache__", ".git", ".tox",
                                                    "node_modules", ".venv", "venv",
                                                    "env", "dist", "build")
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
    A small helper that maintains a stack of enclosing definition names
    (module → class → function → …) as we walk an AST.
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

    Parameters
    ----------
    target_module : str or None
        The module part of the target (e.g. "utils" for "utils.foo").
        None means the target was given without a module prefix.
    target_name : str
        The bare symbol name (e.g. "foo" or "MyClass").
    rel_path : str
        The file path to use in Impact records (repo-relative).
    """

    def __init__(
        self,
        target_module: Optional[str],
        target_name: str,
        rel_path: str,
    ) -> None:
        self._target_module = target_module
        self._target_name = target_name
        self._rel_path = rel_path
        self._stack = _SymbolStack()
        self.impacts: List[Impact] = []

        # Track what local aliases the target_name/target_module were imported as
        # key: local alias, value: original qualified name
        self._aliases: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Scope tracking
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
                ))
        self.generic_visit(node)
        self._stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._stack.push(node.name)
        self.generic_visit(node)
        self._stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    # ------------------------------------------------------------------
    # Import tracking
    # ------------------------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:
        """Handle:  import utils  /  import utils as u"""
        for alias in node.names:
            mod = alias.name          # e.g. "utils"
            local = alias.asname or alias.name

            # Direct module import: `import utils`
            if self._target_module and mod == self._target_module:
                self.impacts.append(Impact(
                    file=self._rel_path,
                    symbol=self._stack.current(),
                    relation="imports",
                    line=node.lineno,
                ))
            # Also track the alias so call-site resolution works later
            if self._target_module and mod == self._target_module:
                self._aliases[local] = mod

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle:  from utils import month_date_range [as x]"""
        mod = node.module or ""
        for alias in node.names:
            imported_name = alias.name          # e.g. "month_date_range"
            local_name = alias.asname or alias.name

            # `from utils import month_date_range`
            target_mod_matches = (
                self._target_module is None or mod == self._target_module
            )
            if target_mod_matches and imported_name == self._target_name:
                self.impacts.append(Impact(
                    file=self._rel_path,
                    symbol=self._stack.current(),
                    relation="imports",
                    line=node.lineno,
                ))
                # Remember: local_name now refers to target
                self._aliases[local_name] = f"{mod}.{imported_name}"

            # `from utils import *` — we can't resolve it precisely, note it
            if imported_name == "*" and self._target_module and mod == self._target_module:
                self.impacts.append(Impact(
                    file=self._rel_path,
                    symbol=self._stack.current(),
                    relation="imports",
                    line=node.lineno,
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
            ))
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Match helpers
    # ------------------------------------------------------------------

    def _matches_name(self, name: str) -> bool:
        """
        True if *name* refers to the target, considering:
          - bare name: "month_date_range"
          - qualified: "utils.month_date_range"
          - alias: whatever the file imported it as
        """
        # Bare name match
        if name == self._target_name:
            return True
        # Fully-qualified match
        if self._target_module and name == f"{self._target_module}.{self._target_name}":
            return True
        # Alias match — check if the name is an alias for the target
        parts = name.split(".", 1)
        alias_root = parts[0]
        alias_attr = parts[1] if len(parts) > 1 else None
        if alias_root in self._aliases:
            resolved = self._aliases[alias_root]
            if alias_attr is None:
                # The alias IS the target symbol
                return resolved == (
                    f"{self._target_module}.{self._target_name}"
                    if self._target_module else self._target_name
                )
            # The alias is the module; check attr matches target name
            return alias_attr == self._target_name
        return False

    def _matches_call(self, called: str) -> bool:
        """Like _matches_name but also handles method calls like self.target()."""
        if self._matches_name(called):
            return True
        # Handle `something.target_name(...)` — e.g. self.month_date_range()
        parts = called.rsplit(".", 1)
        if len(parts) == 2 and parts[1] == self._target_name:
            return True
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_graph(
    repo_path: str | Path,
    target: str,
) -> dict:
    """
    Scan all Python files under *repo_path* for references to *target*.

    Parameters
    ----------
    repo_path : path-like
        Root directory to scan.
    target : str
        Either ``"module.symbol"`` or just ``"symbol"``.

    Returns
    -------
    dict matching the documented graph.json schema.
    """
    repo = Path(repo_path).resolve()

    # Split target into module + name
    if "." in target:
        target_module, target_name = target.rsplit(".", 1)
    else:
        target_module = None
        target_name = target

    all_impacts: List[Impact] = []

    for py_file in _iter_python_files(repo):
        tree = _parse_file(py_file)
        if tree is None:
            continue

        # Make path relative to repo root for cleaner output
        try:
            rel = py_file.relative_to(repo)
        except ValueError:
            rel = py_file

        visitor = _GraphVisitor(
            target_module=target_module,
            target_name=target_name,
            rel_path=str(rel),
        )
        visitor.visit(tree)
        all_impacts.extend(visitor.impacts)

    # Deduplicate: same (file, symbol, relation, line) tuple
    seen: set[tuple] = set()
    unique: List[Impact] = []
    for imp in all_impacts:
        key = (imp.file, imp.symbol, imp.relation, imp.line)
        if key not in seen:
            seen.add(key)
            unique.append(imp)

    # Sort: imports first, then subclasses, then calls; then by file+line
    order = {"imports": 0, "subclasses": 1, "calls": 2}
    unique.sort(key=lambda i: (order.get(i.relation, 9), i.file, i.line))

    return {
        "target": target,
        "impacted": [i.to_dict() for i in unique],
    }


def write_graph(graph: dict, out_path: str | Path) -> None:
    """Serialize *graph* to *out_path* as pretty-printed JSON."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, indent=2)
    print(f"Wrote {len(graph['impacted'])} impact(s) to {out}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build a call/dependency graph for a target Python symbol.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        "--repo", required=True, metavar="PATH",
        help="Root directory of the repository to scan.",
    )
    p.add_argument(
        "--target", required=True, metavar="MODULE.SYMBOL",
        help=(
            "Fully- or partially-qualified target symbol.\n"
            "Examples:\n"
            "  utils.month_date_range\n"
            "  ExpenseTracker\n"
            "  models.Expense"
        ),
    )
    p.add_argument(
        "--out", default="blast_radius/graph.json", metavar="FILE",
        help="Output JSON file (default: blast_radius/graph.json).",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not Path(args.repo).is_dir():
        print(f"Error: repo path '{args.repo}' is not a directory.", file=sys.stderr)
        return 1

    graph = build_graph(args.repo, args.target)
    write_graph(graph, args.out)

    # Also print a summary to stdout
    print(json.dumps(graph, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
