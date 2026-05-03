from __future__ import annotations

import sys
import dataclasses
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "service" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from powermind_rag.config import RAGConfig
from powermind_rag.llm import LocalQwen


def main() -> None:
    cfg_env = RAGConfig.from_env()
    cfg = dataclasses.replace(cfg_env, local_only=False)
    print("Using qwen_model_path:", cfg.qwen_model_path.resolve())
    print("Instantiating LocalQwen directly (no visual models). This will load the Qwen model and may take minutes...")
    llm = LocalQwen(cfg.qwen_model_path, device=cfg.device)

    question = "What is the personal email address of Gautam Adani?"
    system = "You are a grounded QA model with zero hallucination tolerance. If the answer is not present in the provided context, respond exactly with NOT_FOUND."
    user = f"QUESTION:\n{question}\n\nCONTEXT:\n(Use only the provided context — none provided so answer should be NOT_FOUND)"
    print("Running single generation (may take a while)...")
    generated = llm.generate(system=system, user=user, max_new_tokens=256)
    print("--- GENERATED ---")
    print(generated)


if __name__ == "__main__":
    print("WARNING: This will load the local Qwen model and may take several minutes and significant GPU RAM.")
    main()
