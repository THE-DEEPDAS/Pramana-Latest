from __future__ import annotations

import sys
import traceback
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "service" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from powermind_rag.config import RAGConfig
from powermind_rag.pipeline import MultimodalRAGPipeline


def main() -> int:
    question = (
        "In Note 7 of the consolidated financial results, what was the exact legal body "
        "in the United States that filed the indictment against the executive director of "
        "AEL, and in which specific district court was this case filed?"
    )

    cfg = RAGConfig.from_env()
    print("Config:")
    print(f"  local_only={cfg.local_only}")
    print(f"  device={cfg.device}")
    print(f"  storage_dir={cfg.storage_dir.resolve()}")
    print(f"  qwen_model_path={cfg.qwen_model_path.resolve()}")

    try:
        pipeline = MultimodalRAGPipeline(cfg)
        pipeline.load_from_storage()
        ans = pipeline.answer(question)
        print("\nAnswer:\n", ans.text)
        print("\nFallback:", ans.is_fallback)
        print("Citations:", [c.citation for c in ans.retrieved[:5]])
        return 0
    except Exception:
        print("\nERROR during full pipeline execution:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
