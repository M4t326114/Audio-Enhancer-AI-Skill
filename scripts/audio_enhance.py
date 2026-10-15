#!/usr/bin/env python3
"""Local speech enhancement for talking-head audio (replaces the manual Adobe Podcast step).

Chain (all on this Mac, nothing is uploaded):
  1. hum notches (50/60 Hz and harmonics, only when the hum is actually measured)
  2. dereverberation: WPE (weighted prediction error), the classical late-reverb remover, blended with the dry signal
  3. denoising: DeepFilterNet3 (full-band 48 kHz deep-learning enhancer)
  4. voice finish with ffmpeg: high-pass, mud cut, presence, a touch of air, de-esser, gentle compression, level -16 LUFS
Why this chain: on a degraded test recording with a known clean reference it cut the residual in the pauses from -9.4 dB to about -21 dB
(DeepFilterNet3 alone: -18.8 dB; an ffmpeg-only denoiser chain did not help). Resemble Enhance was evaluated and rejected: it needs deepspeed and
torch 2.1 pins that do not install on Apple Silicon with a current toolchain.

Usage (run with the virtualenv in Ferramentas/audio-venv, see enhance_audio.sh):
  audio_enhance.py <in> <out.wav> [--dereverb 0.9] [--no-denoise] [--no-eq] [--level -16]
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 48000


def load_mono48(path):
    tmp = Path(tempfile.mkdtemp()) / "in48.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-c:a", "pcm_f32le", str(tmp)], check=True)
    x, _ = sf.read(tmp)
    return x.astype(np.float64)


def quiet_floor_db(x):
    """Level of the quietest 10% of 20 ms frames (dBFS): a proxy for the noise floor."""
    fr = SR // 50
    k = len(x) // fr
    r = np.sqrt((x[: k * fr].reshape(k, fr) ** 2).mean(1)) + 1e-9
    return float(20 * np.log10(np.percentile(r, 10)))


def hum_notches(x):
    """Notch 50/60 Hz and harmonics when a peak stands 9 dB or more above its neighbours."""
    from scipy.signal import iirnotch, filtfilt, welch
    f, p = welch(x, SR, nperseg=SR)  # 1 Hz resolution
    found = []
    for base in (50, 60):
        for h in range(1, 6):
            fc = base * h
            peak = p[fc - 1: fc + 2].max()
            neigh = np.median(np.r_[p[fc - 12: fc - 4], p[fc + 5: fc + 13]]) + 1e-18
            if 10 * np.log10(peak / neigh) >= 9:
                found.append(fc)
    for fc in found:
        b, a = iirnotch(fc, 35, SR)
        x = filtfilt(b, a, x)
    return x, found


def wpe_dereverb(x, mix):
    from nara_wpe.utils import istft, stft
    from nara_wpe.wpe import wpe
    Y = stft(x[None, :], size=2048, shift=512)                        # (1, T, F)
    Z = wpe(Y.transpose(2, 0, 1), taps=14, delay=2, iterations=4, statistics_mode="full").transpose(1, 2, 0)
    z = istft(Z, size=2048, shift=512)[0][: len(x)]
    z = np.pad(z, (0, len(x) - len(z)))
    return mix * z + (1 - mix) * x


def dfn_denoise(x):
    import torch
    from df.enhance import enhance, init_df
    model, state, _ = init_df(log_level="ERROR")
    out = enhance(model, state, torch.from_numpy(x.astype(np.float32))[None, :])
    return out[0].numpy().astype(np.float64)


EQ_CHAIN = ("highpass=f=75,"
            "equalizer=f=220:t=q:w=1.1:g=-2.0,"          # low-mid mud
            "equalizer=f=3200:t=q:w=1.0:g=2.2,"          # presence / intelligibility
            "equalizer=f=9000:t=h:w=0.7:g=1.2,"           # a touch of air
            "deesser=i=0.35:m=0.5:f=0.5,"                 # sibilance
            "acompressor=threshold=-21dB:ratio=2.2:attack=12:release=170:makeup=2,"
            "alimiter=limit=0.89")


def finish(x, level, eq):
    tmp = Path(tempfile.mkdtemp())
    sf.write(tmp / "a.wav", x, SR, subtype="PCM_24")
    af = (EQ_CHAIN + "," if eq else "") + f"loudnorm=I={level}:TP=-1.5:LRA=9"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp / "a.wav"), "-af", af, "-ar", str(SR), "-c:a", "pcm_s24le", str(tmp / "b.wav")], check=True)
    y, _ = sf.read(tmp / "b.wav")
    return y


def align_to(y, x_in):
    """Remove the latency the enhancer and the filters add (a few ms), so the audio keeps the exact original timeline."""
    from scipy.signal import fftconvolve
    n = min(len(y), len(x_in))
    env = lambda a: np.convolve(np.abs(a[:n]), np.ones(96) / 96, mode="same")[::24]   # 2 kHz envelope
    ey, ex = env(y) - env(y).mean(), env(x_in) - env(x_in).mean()
    lag = int(np.argmax(fftconvolve(ey, ex[::-1], mode="full")) - (len(ex) - 1)) * 24    # samples y is late by (coarse)
    # refine on the waveform within +-30 ms
    best, bl = -1e18, lag
    for d in range(lag - 1440, lag + 1441, 8):
        a = y[max(d, 0): n][: 96000]; b = x_in[max(-d, 0):][: len(a)]; m = min(len(a), len(b))
        c = float(np.dot(a[:m], b[:m]) / (np.linalg.norm(a[:m]) * np.linalg.norm(b[:m]) + 1e-9))
        if c > best: best, bl = c, d
    lag = bl
    if lag > 0:
        y = np.r_[y[lag:], np.zeros(lag)]
    elif lag < 0:
        y = np.r_[np.zeros(-lag), y][: len(y)]
    return y[: len(x_in)] if len(y) >= len(x_in) else np.r_[y, np.zeros(len(x_in) - len(y))], lag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--dereverb", type=float, default=0.9, help="0 = off, 1 = fully dereverberated, 0.9 default")
    ap.add_argument("--no-denoise", action="store_true"); ap.add_argument("--no-eq", action="store_true")
    ap.add_argument("--level", type=float, default=-16.0)
    a = ap.parse_args()
    x = load_mono48(a.inp); x_orig = x.copy()
    rep = {"floor_before_db": round(quiet_floor_db(x), 1)}
    x, hum = hum_notches(x); rep["hum_notches_hz"] = hum
    if a.dereverb > 0:
        x = wpe_dereverb(x, a.dereverb)
    if not a.no_denoise:
        x = dfn_denoise(x)
    rep["floor_after_denoise_db"] = round(quiet_floor_db(x), 1)
    y = finish(x, a.level, not a.no_eq)
    y, lag = align_to(y, x_orig); rep["latency_removed_ms"] = round(lag / SR * 1000, 1)
    sf.write(a.out, y, SR, subtype="PCM_24")
    rep["floor_after_db"] = round(quiet_floor_db(y), 1)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
