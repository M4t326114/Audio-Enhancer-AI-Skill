#!/usr/bin/env python3
"""Voice reconstruction with Sidon (University of Tokyo, MIT license), the open model closest to Adobe Enhance Speech: it re-synthesizes the
voice clean at 48 kHz and removes reverberation, noise, band limitation and codec damage (104 languages, Portuguese included).

Fast path on Apple Silicon: the published frozen graphs are re-bound on the GPU (sidon_gpu.py): the w2v-BERT feature predictor in fp32 and
the DAC vocoder in fp16, decoded in overlapping 1 s windows (memory-bounded). Same output as the reference CPU graphs (correlation 0.99997),
about 5x faster than real time on an M5. Then a light finish (de-esser, gentle compression, -16 LUFS) and the latency is removed so the
audio keeps the exact original timeline.

Usage (Ferramentas/sidon-venv):  sidon_restore.py <in> <out.wav> [--device mps|cpu] [--no-finish] [--level -16]"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio
import transformers

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sidon_gpu  # noqa: E402
from audio_enhance import align_to, load_mono48, quiet_floor_db  # noqa: E402

FINISH = ("highpass=f=70,deesser=i=0.3:m=0.5:f=0.5,"
          "acompressor=threshold=-20dB:ratio=2:attack=10:release=160:makeup=1.5,alimiter=limit=0.89")


def models_dir():
    for d in HERE.parents:
        for c in (d / "modelos" / "sidon", d / "Ferramentas" / "modelos" / "sidon"):
            if (c / "decoder_cpu.pt").is_file():
                return c
    sys.exit("Sidon weights not found (Ferramentas/modelos/sidon)")


def restore(x48, device):
    """x48: mono float64 at 48 kHz. Returns the restored voice at 48 kHz, same length."""
    md = models_dir()
    peak = float(np.abs(x48).max()) or 1.0
    x = torch.from_numpy((0.9 * x48 / peak).astype(np.float32)).view(1, -1)
    x = torchaudio.functional.highpass_biquad(x, 48000, 50)
    x16 = torch.nn.functional.pad(torchaudio.functional.resample(x, 48000, 16000), (0, 24000))
    pre = transformers.SeamlessM4TFeatureExtractor.from_pretrained(str(md / "w2v-bert-2.0-preprocessor"))
    gpu = device == "mps"
    fe = sidon_gpu.load(md / "feature_extractor_cpu.pt", device)
    dec = sidon_gpu.load(md / "decoder_cpu.pt", device, half=gpu)
    feats = []
    with torch.inference_mode():
        for chunk in x16.view(-1).split(16000 * 20):  # 20 s chunks keep the attention memory small on long voice-overs
            inp = pre(torch.nn.functional.pad(chunk, (160, 160)).numpy(), sampling_rate=16000, return_tensors="pt")["input_features"]
            feats.append(fe(inp.to(device))["last_hidden_state"])
        f = torch.cat(feats, dim=1)
        y = sidon_gpu.decode_windowed(dec, f.half() if gpu else f, 50, 16).numpy().astype(np.float64)
    n = len(x48)
    return y[:n] if len(y) >= n else np.pad(y, (0, n - len(y)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    ap.add_argument("--no-finish", action="store_true"); ap.add_argument("--level", type=float, default=-16.0)
    a = ap.parse_args()
    t0 = time.time()
    x = load_mono48(a.inp)
    rep = {"device": a.device, "seconds_audio": round(len(x) / 48000, 2), "floor_before_db": round(quiet_floor_db(x), 1)}
    y = restore(x, a.device)
    t1 = time.time()
    tmp = Path(tempfile.mkdtemp())
    sf.write(tmp / "r.wav", y, 48000, subtype="FLOAT")
    af = (FINISH + "," if not a.no_finish else "") + f"loudnorm=I={a.level}:TP=-1.5:LRA=9"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp / "r.wav"), "-af", af, "-ar", "48000", "-c:a", "pcm_s24le", str(tmp / "f.wav")], check=True)
    z, _ = sf.read(tmp / "f.wav")
    z, lag = align_to(z, x)
    sf.write(a.out, z, 48000, subtype="PCM_24")
    rep.update({"floor_after_db": round(quiet_floor_db(z), 1), "latency_removed_ms": round(lag / 48, 1), "restore_s": round(t1 - t0, 1),
                "total_s": round(time.time() - t0, 1), "realtime_x": round(rep["seconds_audio"] / max(time.time() - t0, 1e-3), 1)})
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
