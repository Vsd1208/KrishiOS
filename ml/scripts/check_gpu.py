"""Verify the local CUDA PyTorch setup (``uv sync --extra gpu`` first).

Usage (from ml/)::

    uv run python scripts/check_gpu.py

Prints the torch/CUDA build, the GPU and its memory, then runs a short fp32 and fp16 (AMP)
matmul benchmark and a tiny timm forward/backward pass, to confirm training works on this GPU.
Exits non-zero if CUDA is unavailable.
"""

from __future__ import annotations

import sys
import time


def _bench(torch, dtype, n: int = 2048, iters: int = 20) -> float:
    a = torch.randn(n, n, device="cuda", dtype=dtype)
    b = torch.randn(n, n, device="cuda", dtype=dtype)
    for _ in range(3):
        a @ b
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters):
        a @ b
    torch.cuda.synchronize()
    secs = (time.perf_counter() - t0) / iters
    return 2 * n**3 / secs / 1e12  # TFLOP/s


def main() -> int:
    try:
        import torch
    except ImportError:
        print("torch is not installed. Run: uv sync --extra gpu")
        return 2
    print(f"torch {torch.__version__} | built for CUDA {torch.version.cuda}")
    if not torch.cuda.is_available():
        print("CUDA NOT available. Check the NVIDIA driver and that the cu130 wheel was installed")
        print("(torch.__version__ should end with '+cu130').")
        return 1
    props = torch.cuda.get_device_properties(0)
    print(f"GPU: {props.name} | compute capability {props.major}.{props.minor} | "
          f"{props.total_memory / 2**30:.1f} GiB")
    print(f"matmul fp32: {_bench(torch, torch.float32):.2f} TFLOP/s")
    print(f"matmul fp16: {_bench(torch, torch.float16):.2f} TFLOP/s")

    try:
        import timm
    except ImportError:
        print("timm not installed (part of the gpu extra).")
        return 1
    model = timm.create_model("mobilenetv3_small_100", pretrained=False, num_classes=10).cuda()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    x = torch.randn(32, 3, 224, 224, device="cuda")
    y = torch.randint(0, 10, (32,), device="cuda")
    with torch.autocast("cuda", dtype=torch.float16):
        loss = torch.nn.functional.cross_entropy(model(x), y)
    loss.backward()
    opt.step()
    peak = torch.cuda.max_memory_allocated() / 2**20
    print(f"timm mobilenetv3_small forward/backward OK (batch 32, AMP) | peak {peak:.0f} MiB")
    print("GPU SETUP OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
