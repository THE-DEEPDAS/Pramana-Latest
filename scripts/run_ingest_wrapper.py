from __future__ import annotations

import sys

sys.path.insert(0, "service/src")

from powermind_rag.cli import main

if __name__ == "__main__":
    import sys as _s
    _s.argv = [
        "prog",
        "ingest-dir",
        "service/data",
        "--doc-type",
        "AEL disclosure pack",
        "--section",
        "Q2 FY26 and H1-26 results",
        "--context",
        "business segments, consolidated income, EBITDA drivers, and airport performance",
    ]
    main()
