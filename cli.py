"""Usage: python cli.py review game.pgn [--depth 18] [--flat] [--save] [--no-cache]"""
import argparse
import sys
from pathlib import Path

from backend import book as book_module
from backend import db
from backend.importers import import_pgn_text
from backend.review import review_game

ORDER = ["Brilliant", "Great", "Book", "Best", "Excellent", "Good", "Inaccuracy", "Mistake", "Miss", "Blunder"]

def cmd_review(args):
    text = Path(args.pgn).read_text(encoding="utf-8")
    conn = None if args.no_cache and not args.save else db.connect()
    book = None if args.no_book else book_module.load()
    if book is None and not args.no_book:
        print("Note: no opening book found (run: python -m backend.book build). Book moves will not be labelled.", file=sys.stderr)

    def progress(done, total):          # shown on stderr, so it never mixes with the table
        print(f"\rAnalysing move {done}/{total}", end="", file=sys.stderr, flush=True)

    result = review_game(text, depth=args.depth, conn=None if args.no_cache else conn,
                         adaptive=not args.flat, on_progress=progress, book=book)
    print("\r" + " " * 30 + "\r", end="", file=sys.stderr)   # clear the progress line
    h = result["headers"]
    print(f"\nReviewing: {h.get('White', '?')} vs {h.get('Black', '?')} ({h.get('Result', '*')}) - {h.get('Event', '')}")
    print(f"Engine Depth: {args.depth}" + (" (deeper as pieces come off)" if not args.flat else " (flat)") + "\n")
    print(f"{'Move':<12} {'Label':<14} {'Drop':<10} Win% (Mover)")
    print("-" * 52)
    counts = {"w": dict.fromkeys(ORDER, 0), "b": dict.fromkeys(ORDER, 0)}
    for m in result["moves"]:
        white = m["ply"] % 2 == 1
        name = f"{(m['ply'] + 1) // 2}. {m['san']}" if white else f"{m['ply'] // 2}... {m['san']}"
        drop = max(0.0, m["win_before"] - m["win_after"])
        drop_s = f"{drop:.1f}%"
        print(f"{name:<12} {m['label']:<14} {drop_s:<10} {m['win_before']:.1f}% -> {m['win_after']:.1f}%")
        counts["w" if white else "b"][m["label"]] += 1
    print("\n" + "=" * 52)
    print("Move Summary:")
    print(f"{'Label':<14} {'White':<8} Black")
    print("-" * 32)
    for label in ORDER:
        print(f"{label:<14} {counts['w'][label]:<8} {counts['b'][label]}")
    print("=" * 52 + "\n")
    if args.save:
        game_id, _ = import_pgn_text(conn, text)[0]
        db.save_moves(conn, game_id, result["moves"])
        print(f"Saved to database as game {game_id}")

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("review")
    r.add_argument("pgn")
    r.add_argument("--depth", type=int, default=18)
    r.add_argument("--flat", action="store_true", help="same depth for every position")
    r.add_argument("--no-book", action="store_true", help="do not label opening-book moves")
    r.add_argument("--save", action="store_true", help="store the reviewed game in the database")
    r.add_argument("--no-cache", action="store_true", help="ignore the eval cache")
    r.set_defaults(func=cmd_review)
    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
