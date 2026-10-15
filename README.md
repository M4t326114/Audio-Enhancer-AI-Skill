# Audio Enhancer Skill

A local tool for cleaning dialogue in videos. It replaces the audio track and copies the original video stream without encoding the video again.

## Contents

- SKILL.md: instructions for using the skill and checking results.
- scripts/tratar_audio.sh: batch processing for extraction, enhancement, loudness, sync, and remuxing.
- scripts/medir.py: measures voice to noise distance before and after treatment.
- scripts/enhance_audio.sh: selects the Sidon or classic engine.
- scripts/sidon_restore.py and scripts/sidon_gpu.py: Sidon voice restoration with Apple Silicon GPU support through PyTorch MPS.
- scripts/audio_enhance.py: the classic enhancement chain.

## Requirements

- macOS with Apple Silicon is recommended for the Sidon MPS GPU path. CPU processing is available but slower.
- Bash, Python 3, ffmpeg, and ffprobe on PATH.
- Python packages for Sidon: numpy, soundfile, torch, torchaudio, and transformers.
- Sidon model files in modelos/sidon/ at the repository root, or in a parent Ferramentas/modelos/sidon/ directory. Required files are feature_extractor_cpu.pt, decoder_cpu.pt, and w2v-bert-2.0-preprocessor/preprocessor_config.json.
- The classic engine also requires its Python dependencies, including SciPy, WPE, and DeepFilterNet3.

Model weights and virtual environments are not included because they are large runtime assets that depend on the target machine. Install compatible packages and download the Sidon weights from the upstream source before using the default engine. Keep the model license and attribution with downloaded weights.

## Usage

Run from the repository root:

```bash
scripts/tratar_audio.sh "/path/to/videos"
scripts/tratar_audio.sh "/path/to/videos" --out "/path/to/output"
scripts/tratar_audio.sh video1.mp4 video2.mov
scripts/tratar_audio.sh "/path/to/videos" --engine classic
```

By default, results go into Áudio tratado/ beside the source videos. See SKILL.md for options and output checks.

## Notes

The originals are left untouched. Sidon reconstructs speech, so music under speech may be removed or changed. Review the result when music or background speech needs to remain.

## Credits

- Audio Enhancer workflow and integration: Mateus Mourão.
- Sidon speech restoration model: SaruLab Speech at the University of Tokyo. Sidon is MIT licensed. The weights are not included. See [Sidon on GitHub](https://github.com/sarulab-speech/Sidon), [Sidon v0.1 on Hugging Face](https://huggingface.co/sarulab-speech/sidon-v0.1), and the [Sidon paper](https://arxiv.org/abs/2509.17052).
- DeepFilterNet and DeepFilterNet3: Rikorose and contributors. The upstream code is available under MIT or Apache 2.0. See [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet).
- WPE dereverberation: NARA-WPE contributors. See [fgnt/nara_wpe](https://github.com/fgnt/nara_wpe).
- Runtime tools: [FFmpeg](https://ffmpeg.org/), [PyTorch](https://pytorch.org/), [torchaudio](https://pytorch.org/audio/stable/index.html), and [Transformers](https://github.com/huggingface/transformers).

This repository contains the integration scripts, not Sidon or DeepFilterNet model weights. Check each upstream project for its license terms, model terms, citations, and notices. The upstream projects do not endorse this repository.
