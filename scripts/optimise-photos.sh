#!/usr/bin/env bash
# Make web-sized, metadata-free AVIF and WebP copies of Mika's photos.
#
# Usage:  scripts/optimise-photos.sh [ORIGINALS_DIR]
#
# ORIGINALS_DIR defaults to the repository root. Originals are NOT committed
# (see .gitignore): they are large and their EXIF data contains GPS location.
# Requires ImageMagick 7 (`magick`) with AVIF and WebP support.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-$ROOT}"
OUT="$ROOT/assets/img"
mkdir -p "$OUT"

# name | source file | crop (WxH+X+Y on the auto-oriented original) | widths
PHOTOS=(
  "hero|IMG_4243.jpeg|2722x3024+520+0|480 800 1200"
  "beach|IMG_4945.jpeg|3024x2016+0+1500|480 800 1200"
  "grass|IMG_4854.jpeg|4032x2688+0+168|480 800 1200"
  "home|dclassic 2026-03-08 122005AB1035BD67CA.jpg|2688x3360+0+300|480 800"
)

for entry in "${PHOTOS[@]}"; do
  IFS='|' read -r name file crop widths <<<"$entry"
  in="$SRC/$file"
  if [[ ! -f "$in" ]]; then
    echo "missing original: $in" >&2
    exit 1
  fi
  for w in $widths; do
    # -strip removes EXIF (including GPS), ICC is converted to sRGB first.
    magick "$in" -auto-orient -crop "$crop" +repage -colorspace sRGB \
      -resize "${w}x" -strip -quality 78 "$OUT/$name-$w.webp"
    magick "$in" -auto-orient -crop "$crop" +repage -colorspace sRGB \
      -resize "${w}x" -strip -quality 55 "$OUT/$name-$w.avif"
  done
  echo "ok  $name"
done

# Social preview image (1200x630, JPEG for widest support in link previews).
magick "$SRC/IMG_4243.jpeg" -auto-orient -crop 4032x2117+0+250 +repage \
  -colorspace sRGB -resize 1200x630 -strip -quality 80 "$OUT/og.jpg"
echo "ok  og"
