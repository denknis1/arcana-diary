"""Shared helpers for API tests."""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_tool(name: str):
    """Import tools/cards/<name>.py by file path (tools/ is not a package)."""
    path = REPO / "tools/cards" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"tools_cards_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
