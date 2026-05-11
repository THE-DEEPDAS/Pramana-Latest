from __future__ import annotations

from pathlib import Path

_SERVICE_PACKAGE = Path(__file__).resolve().parents[1] / "service" / "src" / "powermind_rag"

if not _SERVICE_PACKAGE.exists():
    raise ImportError(f"PowerMind service package not found at {_SERVICE_PACKAGE}")

# Make `python -m powermind_rag.cli` from the repo root resolve submodules from
# service/src before any older installed powermind_rag package in site-packages.
__path__ = [str(_SERVICE_PACKAGE)]
