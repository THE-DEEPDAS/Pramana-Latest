from __future__ import annotations

import os
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "service" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from powermind_rag.config import RAGConfig


def main() -> None:
    cfg = RAGConfig.from_env()
    print("RAGConfig.qwen_model_path (raw env/QWEN_MODEL_PATH):", os.getenv("QWEN_MODEL_PATH"))
    print("Resolved qwen_model_path:", cfg.qwen_model_path.resolve())
    p = cfg.qwen_model_path
    print("Exists:", p.exists())
    print("Is dir:", p.is_dir())
    weights = list(p.glob("**/*.safetensors")) + list(p.glob("**/*.bin"))
    print(f"Found {len(weights)} weight files (first 10):")
    for w in weights[:10]:
        print(" -", w)
    manifest = p / "model.safetensors.index.json"
    print("Index file present:", manifest.exists())


if __name__ == "__main__":
    main()
