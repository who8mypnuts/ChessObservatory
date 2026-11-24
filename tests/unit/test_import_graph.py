"""Architectural guard: dependency rules enforced by parsing the source tree.

This is deliberately a test, not a convention. The rules come from plan §4.1:
``ui`` is the only package allowed to know about Qt; test-only oracles
(``python-chess``, ``networkx``) never appear in ``src``; heavy optional
dependencies stay behind their subsystem boundary.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "chess_observatory"

# top-level module -> directories (relative to the package) allowed to import it
ALLOWLIST: dict[str, set[str]] = {
    "PySide6": {"ui"},
    "numba": {"kernels"},
    "torch": {"ml/training"},
    "onnxruntime": {"ml/inference"},
}

# never allowed anywhere in src, including inside functions
FORBIDDEN_IN_SRC = {"chess", "networkx", "hypothesis", "pytest"}


def source_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def location(path: Path) -> str:
    relative = path.relative_to(SRC).with_suffix("")
    parts = relative.parts[:-1]
    return "/".join(parts)


def resolve_relative(path: Path, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    package = list(path.relative_to(SRC).with_suffix("").parts[:-1])
    climb = node.level - 1
    if climb:
        package = package[:-climb]
    if node.module:
        package.extend(node.module.split("."))
    return ".".join(package)


def imports(path: Path) -> Iterator[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            module = resolve_relative(path, node)
            if module:
                yield node.lineno, module


def violations() -> list[str]:
    problems: list[str] = []
    for path in source_files():
        where = location(path)
        for lineno, module in imports(path):
            top = module.split(".")[0]
            if top in FORBIDDEN_IN_SRC:
                problems.append(f"{path.relative_to(SRC)}:{lineno}: imports test-only '{module}'")
            allowed = ALLOWLIST.get(top)
            if allowed is not None and not any(
                where == prefix or where.startswith(prefix + "/") for prefix in allowed
            ):
                problems.append(
                    f"{path.relative_to(SRC)}:{lineno}: '{module}' is only allowed in "
                    f"{', '.join(sorted(allowed))}/"
                )
            imports_ui = module == "chess_observatory.ui" or module.startswith(
                "chess_observatory.ui."
            )
            if imports_ui and not (
                where in {"ui", "cli"} or where.startswith("ui/") or where.startswith("cli/")
            ):
                problems.append(
                    f"{path.relative_to(SRC)}:{lineno}: only ui/ and cli/ may import '{module}'"
                )
    return problems


def test_source_tree_is_not_empty() -> None:
    assert source_files(), "no source files found; the guard would pass silently"


def test_all_source_files_parse() -> None:
    for path in source_files():
        ast.parse(path.read_text(encoding="utf-8"))


def test_dependency_rules() -> None:
    assert not violations(), "dependency violations:\n" + "\n".join(violations())


def test_qt_stays_in_the_ui_package() -> None:
    qt_users = {
        str(path.relative_to(SRC))
        for path in source_files()
        if any(module.split(".")[0] == "PySide6" for _, module in imports(path))
    }
    assert qt_users == {"ui/launch.py", "ui/main_window.py"}
