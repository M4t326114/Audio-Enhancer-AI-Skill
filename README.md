# Audio Enhancer Skill

A local video-audio cleanup skill. It processes speech, replaces the audio track, and copies the original video stream without re-encoding it.

## Contents

- `SKILL.md` — instructions for using the skill and checking its outputs.
- `scripts/tratar_audio.sh` — batch video workflow: audio extraction, enhancement, loudness normalization, sync handling, and remuxing.
- `scripts/medir.py` — measures voice-to-noise distance before and after treatment.
- `scripts/enhance_audio.sh` — selects the Sidon or classic audio engine.
- `scripts/sidon_restore.py` and `scripts/sidon_gpu.py` — Sidon voice restoration, including Apple Silicon GPU support through PyTorch MPS.
- `scripts/audio_enhance.py` — classic enhancement chain.

## Requirements

- macOS with Apple Silicon is recommended for the Sidon MPS GPU path. The scripts can select CPU when MPS is unavailable, but processing will be slower.
- Bash, Python 3, `ffmpeg`, and `ffprobe` available on `PATH`.
- A Python environment with `numpy`, `soundfile`, `torch`, `torchaudio`, and `transformers` for the Sidon engine.
- Sidon model files placed in `modelos/sidon/` relative to this repository (or in a parent `Ferramentas/modelos/sidon/` directory). The required files are `feature_extractor_cpu.pt`, `decoder_cpu.pt`, and the `w2v-bert-2.0-preprocessor/` directory containing `preprocessor_config.json`.
- For `--engine classic`, a separate Python environment with the dependencies used by `audio_enhance.py`, including SciPy, WPE, and DeepFilterNet3.

Model weights and virtual environments are intentionally not included: they are large, platform-specific runtime assets. Install compatible PyTorch/torchaudio builds for the target machine and obtain the Sidon weights from their upstream source before running the default engine. Keep model licenses and attribution with the downloaded weights.

## Usage

From the repository root:

```bash
scripts/tratar_audio.sh "/path/to/videos"
scripts/tratar_audio.sh "/path/to/videos" --out "/path/to/output"
scripts/tratar_audio.sh video1.mp4 video2.mov
scripts/tratar_audio.sh "/path/to/videos" --engine classic
```

The default output folder is `Áudio tratado/` beside the input videos. See `SKILL.md` for options, output checks, and codec behavior.

## Notes

The original sources are left untouched. The Sidon engine reconstructs speech, so music under speech may be removed or changed. Review the result before delivery, especially when music or background speech must remain.

## Credits

- **Audio Enhancer workflow and integration:** Mateus Mourão.
- **Sidon speech-restoration model:** SaruLab Speech, University of Tokyo. The Sidon model is MIT-licensed. The model weights are not bundled with this repository. See [Sidon on GitHub](https://github.com/sarulab-speech/Sidon), [Sidon v0.1 on Hugging Face](https://huggingface.co/sarulab-speech/sidon-v0.1), and the [Sidon paper](https://arxiv.org/abs/2509.17052).
- **DeepFilterNet / DeepFilterNet3:** Rikorose and contributors. The upstream project offers its code under MIT or Apache-2.0; see [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet).
- **WPE dereverberation:** NARA-WPE contributors; see [fgnt/nara_wpe](https://github.com/fgnt/nara_wpe).
- **Runtime tools and libraries:** [FFmpeg](https://ffmpeg.org/), [PyTorch](https://pytorch.org/), [torchaudio](https://pytorch.org/audio/stable/index.html), and [Transformers](https://github.com/huggingface/transformers).

This repository contains the integration scripts listed above, not the Sidon or DeepFilterNet model weights. Refer to each upstream project for its license terms, model terms, citations, and notices. No upstream project endorses this repository.
