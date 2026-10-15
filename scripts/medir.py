#!/usr/bin/env python3
"""Voice-to-noise distance of a WAV: level of the loud 20 ms frames (90th percentile, the voice) minus the quiet ones (10th percentile, the
floor between words), in dB. Independent of the overall gain, so before/after compare fairly. Usage: medir.py <a.wav> [<b.wav>...]"""
import subprocess
import sys

import numpy as np

for p in sys.argv[1:]:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", "48000", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    k = len(x) // 960
    r = 20 * np.log10(np.sqrt((x[: k * 960].reshape(k, 960) ** 2).mean(1)) + 1e-9)
    print(f"{np.percentile(r, 90) - np.percentile(r, 10):.1f}", end=" ")
print()
