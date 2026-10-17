import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def test_cli_review_prints_table_and_summary():
    pgn = ROOT / "tests" / "data" / "mate_in_one.pgn"
    out = subprocess.run([sys.executable, "cli.py", "review", str(pgn), "--depth", "5", "--no-cache"],
                         cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "Move Summary" in out.stdout
    assert "Qxf7#" in out.stdout