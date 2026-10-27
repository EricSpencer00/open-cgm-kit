"""Route OCK-P1 with Freerouting, then fill planes (KiCad's bundled Python).

  python route_board.py <board.kicad_pcb> <freerouting.jar> [passes]
"""
import subprocess
import sys
from pathlib import Path

import pcbnew


def main(board_path: str, jar: str, passes: int = 100):
    path = Path(board_path)
    dsn, ses = path.with_suffix(".dsn"), path.with_suffix(".ses")
    board = pcbnew.LoadBoard(str(path))
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise SystemExit("DSN export failed")
    subprocess.run(["java", "-jar", jar, "-de", str(dsn), "-do", str(ses), "-mp", str(passes),
                    "--gui.enabled=false"], check=True)
    board = pcbnew.LoadBoard(str(path))
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise SystemExit("SES import failed")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(path), board)
    print(f"routed -> {path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 100)
