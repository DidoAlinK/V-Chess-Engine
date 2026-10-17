"""Command-line interface for V-Chess game review."""

import argparse
from pathlib import Path
import sys

import chess
import chess.pgn

from backend.analysis import Engine
from backend.classify import classify, win_pct


def review_game(pgn_path: str | Path, depth: int = 12) -> None:
    """Analyze a PGN game move-by-move and print classifications and win% drops."""
    path = Path(pgn_path)
    if not path.is_file():
        print(f"Error: PGN file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        game = chess.pgn.read_game(f)

    if game is None:
        print(f"Error: No valid chess game found in {path}", file=sys.stderr)
        sys.exit(1)

    headers = game.headers
    white = headers.get("White", "White")
    black = headers.get("Black", "Black")
    result = headers.get("Result", "*")
    event = headers.get("Event", "Game")

    print(f"\nReviewing: {white} vs {black} ({result}) - {event}")
    print(f"Engine Depth: {depth}\n")
    print(f"{'Move':<12} {'Label':<14} {'Drop':<10} {'Win% (Mover)'}")
    print("-" * 52)

    board = game.board()
    white_counts: dict[str, int] = {}
    black_counts: dict[str, int] = {}

    with Engine() as engine:
        for move in game.mainline_moves():
            ply = board.ply() + 1
            is_white = (ply % 2 == 1)
            move_num = (ply + 1) // 2
            san = board.san(move)
            move_str = f"{move_num}. {san}" if is_white else f"{move_num}... {san}"

            # Mover's winning chances before move
            fen_before = board.fen()
            info_before = engine.analyse(fen_before, depth=depth, multipv=1)[0]
            wb = win_pct(cp=info_before["cp"], mate=info_before["mate"])

            # Make the move
            board.push(move)

            # Mover's winning chances after move
            if board.is_checkmate():
                wa = 100.0
            elif board.is_stalemate() or board.is_insufficient_material():
                wa = 50.0
            else:
                fen_after = board.fen()
                info_after = engine.analyse(fen_after, depth=depth, multipv=1)[0]
                # info_after is from opponent's perspective -> invert for mover
                m_cp = -info_after["cp"] if info_after["cp"] is not None else None
                m_mate = -info_after["mate"] if info_after["mate"] is not None else None
                wa = win_pct(cp=m_cp, mate=m_mate)

            drop = max(0.0, wb - wa)
            label = classify(wb, wa)

            counts = white_counts if is_white else black_counts
            counts[label] = counts.get(label, 0) + 1

            drop_str = f"{drop:.1f}%"
            win_prog = f"{wb:.1f}% -> {wa:.1f}%"
            print(f"{move_str:<12} {label:<14} {drop_str:<10} {win_prog}")

    print("\n" + "=" * 52)
    print("Move Summary:")
    all_labels = ["Best", "Good", "Inaccuracy", "Mistake", "Blunder"]
    print(f"{'Label':<14} {'White':<8} {'Black':<8}")
    print("-" * 32)
    for l in all_labels:
        w_c = white_counts.get(l, 0)
        b_c = black_counts.get(l, 0)
        print(f"{l:<14} {w_c:<8} {b_c:<8}")
    print("=" * 52 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="V-Chess command-line game analysis.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    review_parser = subparsers.add_parser("review", help="Review a PGN game.")
    review_parser.add_argument("pgn", help="Path to the PGN file.")
    review_parser.add_argument(
        "--depth", type=int, default=12, help="Engine search depth (default: 12)."
    )

    args = parser.parse_args()

    if args.command == "review":
        review_game(args.pgn, depth=args.depth)


if __name__ == "__main__":
    main()
