"""Opening book from the free Lichess chess-openings database (public domain).
Build it once:   python -m backend.book build      (writes data/book.json)
"""
import csv
import io
import json
import sys
from pathlib import Path

import chess
import chess.pgn

BOOK_PATH = Path(__file__).resolve().parent.parent / "data" / "book.json"
URL = "https://raw.githubusercontent.com/lichess-org/chess-openings/master/{}.tsv"

def parse_tsv(text, book=None):
    """Add every position of every opening line to the book: {epd: opening name}."""
    book = {} if book is None else book
    for row in csv.DictReader(io.StringIO(text), delimiter="\t"):
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        board = game.board()
        for move in game.mainline_moves():
            board.push(move)
            book.setdefault(board.epd(), row["name"])
    return book

def build(path=BOOK_PATH):
    import httpx
    book = {}
    for letter in "abcde":
        r = httpx.get(URL.format(letter), timeout=30, follow_redirects=True)
        r.raise_for_status()
        parse_tsv(r.text, book)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(book), encoding="utf-8")
    return len(book)

def load(path=BOOK_PATH):
    """Returns the book dict, or None if it has not been built yet."""
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

if __name__ == "__main__":
    if sys.argv[1:] == ["build"]:
        print(build(), "book positions saved to", BOOK_PATH)
    else:
        print("usage: python -m backend.book build")
