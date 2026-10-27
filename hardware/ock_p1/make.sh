#!/bin/sh
# Rebuild the OCK-P1 board from the pinned Biocoin layout. Needs KiCad 10.
set -e
cd "$(dirname "$0")"
KICAD=${KICAD:-$HOME/Applications/KiCad/KiCad.app/Contents}
[ -d "$KICAD" ] || KICAD=/Applications/KiCad/KiCad.app/Contents
CLI=$KICAD/MacOS/kicad-cli
PY=$KICAD/Frameworks/Python.framework/Versions/Current/bin/python3
BUILD=../../build/ock_p1
mkdir -p "$BUILD"
"$CLI" pcb import ../../vendor/biocoin/PCB/Biocoin/design/Biocoin_v1.3.PcbDoc -o "$BUILD/biocoin_v1.3.kicad_pcb"
rm -rf ock_p1.pretty
"$PY" build_board.py "$BUILD/biocoin_v1.3.kicad_pcb" . "$KICAD/SharedSupport/footprints"
"$CLI" pcb drc --format json --severity-error -o "$BUILD/drc.json" ock_p1.kicad_pcb
"$CLI" pcb render --side top --width 1600 --height 1300 --quality high -o render_top.png ock_p1.kicad_pcb
"$CLI" pcb render --side bottom --width 1600 --height 1300 --quality high -o render_bottom.png ock_p1.kicad_pcb
