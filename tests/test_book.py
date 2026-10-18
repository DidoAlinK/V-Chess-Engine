import json
import chess
from backend import book

TSV = "eco\tname\tpgn\nB00\tKing's Pawn\t1. e4\nC20\tKing's Pawn Game\t1. e4 e5\n"

def test_parse_tsv_adds_every_position_of_every_line():
    b = book.parse_tsv(TSV)
    board = chess.Board()
    board.push_san("e4")
    assert b[board.epd()] == "King's Pawn"          # first name wins for a shared position
    board.push_san("e5")
    assert b[board.epd()] == "King's Pawn Game"
    assert len(b) == 2

def test_load_returns_none_when_missing_and_dict_when_present(tmp_path):
    assert book.load(tmp_path / "nope.json") is None
    p = tmp_path / "book.json"
    p.write_text(json.dumps({"x": "y"}))
    assert book.load(p) == {"x": "y"}
