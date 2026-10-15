---
name: audio-enhancer
description: Treat and clean dialogue audio in video files while preserving the original picture. Use when asked to clean, improve, or enhance audio without editing the video.
---

# Audio Enhancer

Treat the voice and return the same videos with the same picture, name, and length. This is the audio stage of Editor-Cortes on its own, with no cuts or motion edits.

The helper scripts are in the `scripts/` folder. Sidon model weights and Python environments must be installed separately; see [README.md](README.md).

## 1. Intake

Ask only for the folder containing the videos, or for the files, if the user has not provided them. This skill does not edit the video or create a company folder.

## 2. Run

```bash
scripts/tratar_audio.sh "<video folder>"                  # output: "<folder>/Áudio tratado/"
scripts/tratar_audio.sh "<folder>" --out "<other folder>" # choose another output folder
scripts/tratar_audio.sh video1.mp4 video2.mov              # process individual files
```

For many videos, run the script in the background. It prints one line per video and writes `relatorio.txt` in the output folder. If an output is newer than its source, that video is skipped so a rerun can continue where it stopped.

For each video, the workflow:

1. Extracts audio as 48 kHz mono. Two-mic recordings are mixed down; videos without audio are skipped and reported.
2. Uses Sidon voice reconstruction on the GPU to remove room reverb, noise, hum, bandwidth limits, and codec damage, then resynthesizes the voice at 48 kHz.
3. Applies a light finish: high-pass filter, de-esser, and gentle compression.
4. Targets -14 LUFS integrated and -1.5 dB true peak with two-pass linear normalization, preserving voice dynamics.
5. Removes processing latency to keep the audio aligned with the original timeline. Measured sync on real clips is under 10 ms.
6. Copies the original video stream bit for bit (`-c:v copy`), preserving resolution, frame rate, bitrate, rotation, and metadata. The new audio is stereo (dual mono): MP4 and M4V use AAC at 320 kb/s; MOV, MXF, and MTS become MOV with 24-bit PCM for editing. Camera data tracks such as timecode and Sony rtmd are not carried over.

Options:

- `--level -16`: choose a different loudness target.
- `--engine classic`: use the previous chain (hum notches, WPE dereverb, DeepFilterNet3, voice EQ). Choose it for already clean, close-miked recordings or if Sidon makes a voice sound artificial.
- `--keep`: keep intermediate WAV files in `.work/` for comparison.

## 3. Check the results

1. Read `relatorio.txt`. Check that input and output durations match within a few milliseconds, loudness is around -14 LUFS, and the voice-to-noise value improves. A drop, or a gain below about 2 dB on a noisy source, needs review.
2. Listen to the voice. Run once with `--keep` and compare a few seconds of `original.wav` and `final.wav`. The `scripts/medir.py` script prints the voice-to-noise distance. Check pauses and sentences for metallic or phasey vowels, clipped words, breaths turned into noise, or incorrect reconstruction of music/background speech. Sidon can remove or distort music under speech. If the music needs to stay, or the voice sounds artificial, redo it with `--engine classic` and mention that choice.
3. Use ffprobe to compare an output with its source: video codec, size, bitrate, and rotation side data should match.

## 4. Hand back

Tell the user where the processed files are (usually `Áudio tratado/` next to the originals) and summarize each video's duration, LUFS, voice-to-noise gain, engine used, and anything unusual, such as missing audio, music removal, or use of the classic engine.

The original files are never modified, moved, or overwritten.
