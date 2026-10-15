---
name: Audio-Enhancer-Skill
description: Tratar-Audio - treats the voice of a batch of videos and gives them back exactly as they were, with only the audio replaced. Sidon voice reconstruction on the Mac's GPU (removes room reverb and noise, re-synthesizes the voice clean at 48 kHz - the closest open model to Adobe Enhance Speech), a light finish, -14 LUFS, latency removed so lip sync is exact, and the original picture copied bit for bit (no re-encode). Use when the user asks to tratar/limpar/melhorar o áudio of videos without editing them, or says Tratar-Audio.
---

# Audio Enhancer Skill

Take the videos, treat the voice, and hand the same videos back: same picture, same name, same length, only a clean voice. It is the audio stage of Editor-Cortes on its own, with no cut and no motion.

`T` = the `scripts/` folder in this repository. The audio helper scripts are included here. The Sidon model weights and Python environments must be installed separately; see `README.md`.

## 1. Intake

Ask only for the folder with the videos (or the files), if the user did not give it. Do not create a company folder: this skill does not edit. Ask nothing else unless something below needs a decision.

## 2. Run

```bash
scripts/tratar_audio.sh "<pasta dos vídeos>"                       # -> "<pasta>/Áudio tratado/", same file names
scripts/tratar_audio.sh "<pasta>" --out "<outra pasta>"            # elsewhere
scripts/tratar_audio.sh video1.mp4 video2.mov                       # single files
```
Run it in the background (`run_in_background: true`) when there are many videos; it prints one line per video and writes `relatorio.txt` in the output folder. A video already treated (output newer than its source) is skipped, so a re-run continues where it stopped.

Per video, about 10 s for 40 s of speech:
1. **Audio extracted** to 48 kHz mono (a two-mic recording is mixed down; a video with no audio is skipped and reported).
2. **Sidon voice reconstruction** on the GPU: room reverberation, noise, hum, band limitation and codec damage removed, and the voice re-synthesized at 48 kHz.
3. **Finish**: high-pass, de-esser, gentle compression.
4. **Loudness** -14 LUFS integrated, true peak -1.5 dB, by two-pass linear normalization, so the voice dynamics are not touched.
5. **Latency removed**, so the voice sits on the exact original timeline. Sync measured on real clips: under 10 ms, where lip sync is perceptible from about 40 ms.
6. **Remux**: the original video stream is copied bit for bit (`-c:v copy`): same resolution, frame rate, bitrate, rotation and metadata. The new audio goes in as stereo (dual mono):
   - `.mp4` and `.m4v` get AAC at 320 kb/s and keep their name and extension;
   - `.mov`, `.mxf` and `.mts` become a `.mov` with 24-bit PCM, which suits editing.
   Camera data tracks (timecode, Sony rtmd) are not carried over.

Options:
- `--level -16` for another loudness.
- `--engine classic` for the previous chain (hum notches, WPE dereverb, DeepFilterNet3, voice EQ). Use it for a recording that is already clean and close-miked, where a generative model would only re-synthesize what is fine, or when Sidon sounds artificial on a voice.
- `--keep` keeps the intermediate WAVs in `.work/`, for comparing before and after.

## 3. Check before handing back

1. **Read `relatorio.txt`.** Every video must show:
   - duration in = duration out (within a few ms);
   - about -14 LUFS;
   - "voz acima do ruído" up after treatment. This is the distance between the voice and the floor between words, so it does not change with the overall volume. A drop, or a gain under about 2 dB on a noisy source, means a look is needed.
2. **Check the voice itself.** Run once with `--keep` and compare a few seconds of `original.wav` and `final.wav` (`scripts/medir.py` prints the voice-to-noise distance). On every video, also check the spectrum of a pause and of a sentence (`ffmpeg -ss <t> -t 3 -i final.wav -lavfi showspectrumpic=s=800x300 x.png` and look at it) for these failure signs:
   - metallic or "phasey" vowels;
   - words cut or swallowed;
   - breaths turned into noise;
   - a wrong voice in music or background speech. Sidon rebuilds speech, so music under the voice is removed or distorted.
   If a video has music that must stay, or sounds artificial, redo it with `--engine classic` and say so.
3. `ffprobe` one output against its source: the same video codec, size and bitrate, and the rotation side data kept.

## 4. Hand back

Tell the user where the files are (`Áudio tratado/` next to the originals, unless they asked for another place), and the per-video lines of the report in short form:
- duration;
- LUFS;
- the voice-to-noise gain;
- which engine was used;
- anything doubtful: a video with no audio, music removed, classic used.

The originals are never modified, moved or overwritten.
