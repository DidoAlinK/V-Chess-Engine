"""Get games into the database from a PGN file, chess.com, or Lichess.
Run from the project root:
    python -m backend.importers pgn path/to/file.pgn
    python -m backend.importers chesscom USERNAME 2026 10
    python -m backend.importers lichess USERNAME --max 20
"""
import argparse
import hashlib
import io
from pathlib import Path

import chess.pgn
import httpx

from backend import db

HEADERS = {"User-Agent": "V-Chess/0.1 (personal chess review tool)"}

def _source_id(game, text):
    """A stable id so importing the same game twice doesn't duplicate it."""
    for key in ("Link", "Site"):
        value = game.headers.get(key, "")
        if value.startswith("http"):
            return value
    return hashlib.sha1(text.encode()).hexdigest()[:16]

def import_pgn_text(conn, pgn_text, source="pgn"):
    """Store every game found in pgn_text. Returns a list of (game_id, created)."""
    results = []
    stream = io.StringIO(pgn_text)
    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        text = game.accept(exporter)
        h = game.headers
        results.append(db.add_game(
            conn, source=source, source_id=_source_id(game, text),
            white=h.get("White"), black=h.get("Black"), result=h.get("Result"),
            played_at=h.get("Date"), pgn=text))
    return results

def fetch_chesscom(user, year, month):
    """Download one month of games as PGN text."""
    url = f"https://api.chess.com/pub/player/{user.lower()}/games/{year}/{month:02d}"
    r = httpx.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return "\n\n".join(g["pgn"] for g in r.json().get("games", []) if g.get("pgn"))

def fetch_lichess(user, max_games=20):
    r = httpx.get(f"https://lichess.org/api/games/user/{user}", params={"max": max_games},
                  headers={**HEADERS, "Accept": "application/x-chess-pgn"}, timeout=60)
    r.raise_for_status()
    return r.text

def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m backend.importers")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("pgn"); f.add_argument("file")
    c = sub.add_parser("chesscom"); c.add_argument("user"); c.add_argument("year", type=int); c.add_argument("month", type=int)
    l = sub.add_parser("lichess"); l.add_argument("user"); l.add_argument("--max", type=int, default=20)
    args = p.parse_args(argv)

    if args.cmd == "pgn":
        text, source = Path(args.file).read_text(encoding="utf-8"), "pgn"
    elif args.cmd == "chesscom":
        text, source = fetch_chesscom(args.user, args.year, args.month), "chesscom"
    else:
        text, source = fetch_lichess(args.user, args.max), "lichess"

    results = import_pgn_text(db.connect(), text, source)
    new = sum(1 for _, created in results if created)
    print(f"{len(results)} games found, {new} new, {len(results) - new} already in the database")

if __name__ == "__main__":
    main()
