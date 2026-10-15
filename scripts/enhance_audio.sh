#!/usr/bin/env bash
# Voice treatment for talking-head audio, all local. Default engine: Sidon voice reconstruction on the Apple GPU (dereverb + denoise +
# restoration at 48 kHz, the closest open model to Adobe Enhance Speech), then a light finish and -16 LUFS. The output keeps the original
# timeline (same duration, latency removed).
# Usage: enhance_audio.sh <audio_original.wav> <audio_enhanced.wav> [--engine sidon|classic] [extra options of the engine]
#   classic = the previous chain (hum notches, WPE dereverb, DeepFilterNet3, voice EQ): faster on very long files, weaker on reverb.
set -euo pipefail
in="$1"; out="$2"; shift 2
engine="sidon"; [ "${1:-}" = "--engine" ] && { engine="$2"; shift 2; }
here="$(cd "$(dirname "$0")" && pwd)"
find_venv() { local d="$here"; while [ "$d" != "/" ]; do for c in "$d/$1" "$d/Ferramentas/$1"; do [ -x "$c/bin/python" ] && { echo "$c"; return; }; done; d="$(dirname "$d")"; done; }
if [ "$engine" = "sidon" ]; then
  venv="$(find_venv sidon-venv)"
  [ -n "$venv" ] || { echo "sidon-venv not found: see the Editor-Cortes SKILL.md (Audio) to create it, or use --engine classic" >&2; exit 1; }
  "$venv/bin/python" "$here/sidon_restore.py" "$in" "$out" "$@"
else
  venv="$(find_venv audio-venv)"
  [ -n "$venv" ] || { echo "audio-venv not found: see the Editor-Cortes SKILL.md (Audio)" >&2; exit 1; }
  "$venv/bin/python" "$here/audio_enhance.py" "$in" "$out" "$@"
fi
a=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in"); b=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out")
echo "durations: in ${a}s, out ${b}s"
