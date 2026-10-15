#!/usr/bin/env bash
# Tratar-Audio: treats the voice of every video and gives the videos back exactly as they were, with only the audio replaced.
#   per video: audio extracted (48 kHz mono) -> Sidon voice reconstruction on the GPU (dereverb, denoise, restoration) -> light finish
#   (high-pass, de-esser, gentle compression) -> -14 LUFS, true peak -1.5 dB -> latency removed (same timeline as the picture) ->
#   remuxed with the ORIGINAL video stream copied bit for bit (no re-encode, same resolution, frame rate, rotation and metadata).
# Usage: tratar_audio.sh <folder or video files...> [--out <folder>] [--level -14] [--engine sidon|classic] [--keep]
#   default output: "<folder of the first video>/Áudio tratado/", same file names. Videos already treated (output newer than input) are
#   skipped. .mp4/.m4v get AAC 320 kb/s stereo; .mov/.mxf/.mts get 24-bit PCM stereo in a .mov (editor-friendly).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
K="$here"
out=""; level="-14"; engine="sidon"; keep=0; inputs=()
while [ $# -gt 0 ]; do
  case "$1" in
    --out) out="$2"; shift 2;; --level) level="$2"; shift 2;; --engine) engine="$2"; shift 2;; --keep) keep=1; shift;;
    *) inputs+=("$1"); shift;;
  esac
done
[ ${#inputs[@]} -gt 0 ] || { echo "usage: tratar_audio.sh <folder or videos...> [--out dir] [--level -14] [--engine sidon|classic] [--keep]" >&2; exit 1; }
shopt -s nullglob nocaseglob
vids=()
for i in "${inputs[@]}"; do
  if [ -d "$i" ]; then for v in "$i"/*.{mp4,mov,m4v,mxf,mts}; do vids+=("$v"); done; else vids+=("$i"); fi
done
[ ${#vids[@]} -gt 0 ] || { echo "no videos found in: ${inputs[*]}" >&2; exit 1; }
[ -n "$out" ] || out="$(cd "$(dirname "${vids[0]}")" && pwd)/Áudio tratado"
mkdir -p "$out"; work="$out/.work"; mkdir -p "$work"
report="$out/relatorio.txt"; : > "$report.tmp"
for v in "${vids[@]}"; do
  base="$(basename "$v")"; n="${base%.*}"; ext="$(echo "${base##*.}" | tr '[:upper:]' '[:lower:]')"
  case "$ext" in mp4|m4v) dst="$out/$base"; acodec=(-c:a aac -b:a 320k);; *) dst="$out/$n.mov"; acodec=(-c:a pcm_s24le);; esac
  if [ -f "$dst" ] && [ "$dst" -nt "$v" ]; then echo "já tratado: $base"; grep -F "$base" "$report" >> "$report.tmp" 2>/dev/null || true; continue; fi
  t0=$(date +%s); w="$work/$n"; mkdir -p "$w"
  if ! ffprobe -v error -select_streams a:0 -show_entries stream=index -of csv=p=0 "$v" | grep -q .; then
    echo "SEM ÁUDIO: $base (pulado)" | tee -a "$report.tmp"; continue
  fi
  ffmpeg -y -loglevel error -i "$v" -vn -ac 1 -ar 48000 -c:a pcm_s16le "$w/original.wav"
  if [ "$engine" = "sidon" ]; then
    "$K/enhance_audio.sh" "$w/original.wav" "$w/tratado.wav" --engine sidon --level "$level" > "$w/sidon.log" 2>&1
  else
    "$K/enhance_audio.sh" "$w/original.wav" "$w/tratado.wav" --engine classic --level "$level" > "$w/sidon.log" 2>&1
  fi
  # exact loudness: two-pass linear loudnorm (no dynamics change, true peak -1.5 dB)
  m=$(ffmpeg -hide_banner -nostats -i "$w/tratado.wav" -af "loudnorm=I=$level:TP=-1.5:LRA=11:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
  mi=$(echo "$m" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}\")")
  ffmpeg -y -loglevel error -i "$w/tratado.wav" -af "loudnorm=I=$level:TP=-1.5:LRA=11:$mi:linear=true,aresample=48000" -c:a pcm_s24le "$w/final.wav"
  # picture copied untouched; only the first video stream and the new audio (dual mono), metadata and rotation kept
  ffmpeg -y -loglevel error -i "$v" -i "$w/final.wav" -map 0:v:0 -map 1:a:0 -map_metadata 0 -c:v copy "${acodec[@]}" -ac 2 -ar 48000 \
    $( [ "$ext" = mp4 ] || [ "$ext" = m4v ] && echo "-movflags +faststart" ) "$dst"
  dv=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$v"); do_=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$dst")
  lufs=$(ffmpeg -hide_banner -nostats -i "$dst" -map 0:a -af ebur128=peak=true -f null - 2>&1 | awk '/Integrated loudness/{f=1} f&&/I:/{print $2; exit}')
  lat=$(grep -h '^{' "$w/sidon.log" | tail -1 | python3 -c "import json,sys; print(json.load(sys.stdin).get('latency_removed_ms','?'))" 2>/dev/null || echo "?")
  set -- $(python3 -I "$here/medir.py" "$w/original.wav" "$w/final.wav")
  line="$base -> $(basename "$dst") | duração ${dv}s -> ${do_}s | ${lufs} LUFS | voz acima do ruído ${1} -> ${2} dB | latência removida ${lat} ms | $(( $(date +%s) - t0 ))s"
  echo "$line" | tee -a "$report.tmp"
  [ "$keep" = 1 ] || rm -rf "$w"
done
mv "$report.tmp" "$report"; [ "$keep" = 1 ] || rmdir "$work" 2>/dev/null || true
echo "pronto: $out (relatório: $report)"
