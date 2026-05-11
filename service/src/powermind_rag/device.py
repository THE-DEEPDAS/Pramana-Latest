from __future__ import annotations


def resolve_device(requested: str) -> str:
    requested = requested.lower().strip()
    if requested in {"api", "remote"}:
        return "api"
    if requested == "cpu":
        return "cpu"
    if requested not in {"cuda", "gpu"}:
        raise ValueError("POWERMIND_DEVICE must be 'api', 'cuda', or 'cpu'.")

    try:
        import torch
    except ImportError:
        return "api"

    if not torch.cuda.is_available():
        return "api"
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
