from __future__ import annotations


def resolve_device(requested: str) -> str:
    requested = requested.lower().strip()
    if requested == "cpu":
        return "cpu"
    if requested not in {"cuda", "gpu"}:
        raise ValueError("POWERMIND_DEVICE must be 'cuda' or 'cpu'.")

    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("GPU execution requires torch. Install torch in the torch_env conda environment.") from exc

    if not torch.cuda.is_available():
        raise RuntimeError(
            "GPU execution is the default, but CUDA is not available. "
            "Activate conda env 'torch_env' with an RTX 5050 / sm_120-compatible PyTorch build, "
            "or set POWERMIND_DEVICE=cpu."
        )
    return "cuda"


def describe_cuda() -> str:
    try:
        import torch
    except ImportError:
        return "torch not installed"
    if not torch.cuda.is_available():
        return "CUDA unavailable"
    props = torch.cuda.get_device_properties(0)
    return f"{props.name}, compute capability sm_{props.major}{props.minor}"
