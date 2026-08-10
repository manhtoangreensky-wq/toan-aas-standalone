from __future__ import annotations

import ast
from pathlib import Path
import re


MODULE_PATH = Path(__file__).resolve().parents[1] / "copyfast_route_engine.py"
FORBIDDEN_IMPORT_ROOTS = {
    "bot",
    "copyfast_bridge",
    "copyfast_db",
    "copyfast_api",
    "httpx",
    "requests",
    "subprocess",
    "os",
    "sqlite3",
    "payos",
    "payment",
    "payments",
    "wallet",
}
FORBIDDEN_CALL_NAMES = {
    "open",
    "__import__",
    "eval",
    "exec",
    "system",
    "popen",
    "connect",
    "request",
    "get",
    "post",
}
FORBIDDEN_LITERAL_PATTERNS = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(
        r"(?:api[_-]?key|access[_-]?token|client[_-]?secret|secret[_-]?key)\s*[:=]\s*['\\\"]?[A-Za-z0-9_-]{12,}",
        re.IGNORECASE,
    ),
)


def imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_route_engine_has_no_provider_network_database_or_payment_import() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))

    assert not imported_roots(tree).intersection(FORBIDDEN_IMPORT_ROOTS)


def test_route_engine_has_no_executable_io_or_provider_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert not call_names.intersection(FORBIDDEN_CALL_NAMES)


def test_route_engine_exposes_only_pure_standard_library_dependencies() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))

    assert imported_roots(tree).issubset({"__future__", "dataclasses", "enum", "math", "typing"})


def test_route_engine_has_no_provider_url_or_credential_shaped_literal() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    string_literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and type(node.value) is str
    ]

    assert all(
        not pattern.search(value)
        for value in string_literals
        for pattern in FORBIDDEN_LITERAL_PATTERNS
    )
