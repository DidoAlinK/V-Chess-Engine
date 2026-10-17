"""Test for CLI review command."""

from pathlib import Path
from cli import review_game


def test_cli_review(capsys):
    pgn_path = Path(__file__).resolve().parent.parent / "game.pgn"
    review_game(pgn_path, depth=5)
    captured = capsys.readouterr()
    assert "Reviewing:" in captured.out
    assert "1. e4" in captured.out
    assert "3... Nf6" in captured.out
    assert "Blunder" in captured.out
    assert "Move Summary:" in captured.out
