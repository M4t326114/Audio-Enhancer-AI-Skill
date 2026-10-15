"""Runs Sidon's frozen TorchScript graphs on the Apple GPU (MPS).

The published Sidon weights are frozen TorchScript graphs whose constants (all the weights) are pinned to the CPU, so they cannot be moved
to the GPU. Both graphs only use plain tensor ops, so this module re-reads their code, binds the constants on the chosen device and runs the
very same computation as ordinary PyTorch. The output matches the CPU graphs (checked in the skill's benchmark) and runs on the GPU."""
import re
import torch
import torch.nn.functional as F

_DT = {3: torch.int32, 4: torch.int64, 5: torch.float16, 6: torch.float32, 7: torch.float64, 15: torch.bfloat16}


class _T:
    """Stands in for `torch.` inside the graph code: the ops the frozen graphs use, made device-agnostic."""
    def __init__(self, dev):
        self.dev = dev

    def __getattr__(self, name):
        return getattr(torch, name)

    def device(self, _):
        return self.dev

    def size(self, x, d=None):
        return list(x.size()) if d is None else x.size(d)

    def view(self, x, shape):
        return x.reshape(shape)

    def to(self, x, dtype, *a, **k):
        return x.to(_DT.get(dtype, dtype) if isinstance(dtype, int) else dtype)

    def arange(self, *a, dtype=None, layout=None, device=None, pin_memory=None):
        return torch.arange(*a, dtype=_DT.get(dtype, dtype) if isinstance(dtype, int) else dtype, device=self.dev)

    def silu(self, x):
        return F.silu(x)

    def glu(self, x, dim=-1):
        return F.glu(x, dim)

    def pad(self, x, p, mode="constant", value=None):
        return F.pad(x, p, mode, 0.0 if value is None else value)

    def einsum(self, eq, ops):
        return torch.einsum(eq, *ops)

    def softmax(self, x, dim, dtype=None):
        return torch.softmax(x, dim)


def load(path, device, half=False):
    m = torch.jit.load(str(path), map_location="cpu")
    code, consts = m.code_with_constants
    fl = torch.float16 if half else torch.float32
    C = {k: v.to(device, dtype=fl if v.is_floating_point() else v.dtype) for k, v in consts.const_mapping.items()}  # the GPU has no float64; half=True runs in fp16
    src = re.sub(r"def forward\(self,\s*(\w+)\s*:[^)]*\)\s*->\s*[^:]+:", r"def forward(\1):", code, count=1)
    src = re.sub(r"CONSTANTS\.(c\d+)", r'C["\1"]', src)
    src = re.sub(r"\btorch\.", "T.", src)
    ns = {"T": _T(torch.device(device)), "C": C}
    exec(compile(src, str(path), "exec"), ns)
    return ns["forward"]


def decode_windowed(dec, feat, win=250, ctx=32):
    """Runs the DAC vocoder over the features in windows of `win` frames (50 frames = 1 s) with `ctx` frames of context on each side,
    keeping only each window's center: seamless (the vocoder is convolutional) and memory-bounded on the GPU. feat: (1, T, 1024)."""
    T = feat.shape[1]; outs = []
    for a in range(0, T, win):
        b = min(T, a + win); lo = max(0, a - ctx); hi = min(T, b + ctx)
        y = dec(feat[:, lo:hi].transpose(1, 2)).reshape(-1)
        outs.append(y[(a - lo) * 960:(a - lo) * 960 + (b - a) * 960].float().cpu())
    return torch.cat(outs)
