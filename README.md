# Audio Enhancer AI Skill

Clean up dialogue in videos with this skill. It works with both **Codex** and **Claude Code**.

It improves the spoken audio and puts it back into the video while keeping the original picture unchanged. Sidon is the default option. You can choose the classic audio engine if Sidon does not sound right for a particular voice or recording.

## What’s included

- `SKILL.md` helps Codex and Claude Code discover the skill.
- `Audio-Enhancer.md` contains the full workflow, options, and quality checks.
- `scripts/` contains the video processing and audio enhancement tools.

## What you need

- macOS with Apple Silicon is recommended for faster Sidon processing. CPU processing is also available.
- Bash, Python 3, `ffmpeg`, and `ffprobe`.
- For Sidon: Python packages `numpy`, `soundfile`, `torch`, `torchaudio`, and `transformers`.
- Sidon model files in `modelos/sidon/` at the repository root. See `Audio-Enhancer.md` for the filenames.
- The classic engine also needs SciPy, WPE, and DeepFilterNet3.

The model weights and Python environments are not included. They are large and depend on your machine, so install them separately before running the skill.

## Use it

From the repository folder, run:

```bash
scripts/tratar_audio.sh "/path/to/videos"
```

To save the results somewhere else:

```bash
scripts/tratar_audio.sh "/path/to/videos" --out "/path/to/output"
```

By default, treated videos are saved in an `Áudio tratado` folder beside the originals. The originals are left untouched. For more options and checks, see `Audio-Enhancer.md`.

## Credits

- Audio Enhancer workflow and integration: Mateus Mourão.
- Sidon speech restoration model: SaruLab Speech at the University of Tokyo. Sidon is MIT licensed. Its weights are not included. See [Sidon on GitHub](https://github.com/sarulab-speech/Sidon), [Sidon v0.1 on Hugging Face](https://huggingface.co/sarulab-speech/sidon-v0.1), and the [Sidon paper](https://arxiv.org/abs/2509.17052).
- DeepFilterNet and DeepFilterNet3: Rikorose and contributors. The upstream code is available under MIT or Apache 2.0. See [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet).
- WPE dereverberation: NARA-WPE contributors. See [fgnt/nara_wpe](https://github.com/fgnt/nara_wpe).
- Runtime tools: [FFmpeg](https://ffmpeg.org/), [PyTorch](https://pytorch.org/), [torchaudio](https://pytorch.org/audio/stable/index.html), and [Transformers](https://github.com/huggingface/transformers).

This repository contains the integration scripts, not Sidon or DeepFilterNet model weights. Check each upstream project for its license terms, model terms, and citations. The upstream projects do not endorse this repository.
