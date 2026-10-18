"""Review a game: analyse every position once (plus a 2nd line when needed), then label every move."""
import io

import chess
import chess.pgn

from backend import db
from backend.analysis import Engine
from backend.classify import classify, win_pct

ENGINE_NAME = "stockfish"
VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
GAP_MIN_WIN, GAP_MAX_WIN = 25.0, 75.0   # only look for "only moves" in undecided positions
SAC_MIN_LOSS = 2                         # points of material given up (a minor piece for a pawn = 2)
PV_PLIES = 6

def depth_for(board, base=18):
    """Search deeper as material comes off: fewer pieces make each search cheaper.
    Depends only on the position, so the cache key stays stable."""
    pieces = chess.popcount(board.occupied)
    if pieces >= 24:
        return base            # opening / early middlegame
    if pieces >= 16:
        return base + 2
    if pieces >= 10:
        return base + 6
    if pieces >= 6:
        return base + 12
    return base + 22           # 3-5 pieces: depth ~40 is still instant

def material_balance(board, color):
    """Material (P=1 N=3 B=3 R=5 Q=9) of `color` minus the opponent's."""
    return sum(v * (len(board.pieces(p, color)) - len(board.pieces(p, not color))) for p, v in VALUES.items())

def is_sacrifice(board_before, move, pv):
    """True if, after the engine's line (`pv` starts with the opponent's reply), the mover is
    down at least SAC_MIN_LOSS points of material compared with before the move."""
    n = min(len(pv), PV_PLIES) // 2 * 2          # an even number of plies: the line ends on the mover's move
    mover = board_before.turn
    before = material_balance(board_before, mover)
    b = board_before.copy()
    b.push(move)
    for uci in pv[:n]:
        m = chess.Move.from_uci(uci)
        if m not in b.legal_moves:
            return False
        b.push(m)
    return material_balance(b, mover) - before <= -SAC_MIN_LOSS

def _lines(eng, conn, fen, depth, need=1):
    """Engine lines for a position (cached). `need` = how many lines are required."""
    if conn is not None:
        cached = db.get_eval(conn, fen, ENGINE_NAME, depth)
        if cached and len(cached) >= need:
            return cached
    lines = eng.analyse(fen, depth, need)
    if conn is not None:
        db.put_eval(conn, fen, ENGINE_NAME, depth, lines)
    return lines

def _position(eng, conn, board, depth, adaptive=True):
    """(win% for the side to move, engine's best move as uci or None, engine lines)."""
    if board.is_checkmate():
        return 0.0, None, []        # side to move has been mated
    if board.is_game_over():
        return 50.0, None, []       # stalemate / draw
    d = depth_for(board, depth) if adaptive else depth
    lines = _lines(eng, conn, board.fen(), d)
    return win_pct(lines[0]["cp"], lines[0]["mate"]), lines[0]["move_uci"], lines

def review_game(pgn_text, depth=18, conn=None, on_progress=None, adaptive=True, book=None):
    """depth is the BASE depth (opening); with adaptive=True it grows as pieces come off.
    book: dict {epd: opening name} (see backend/book.py) or None for no Book labels.
    Returns {"headers": {...}, "moves": [{ply, san, uci, fen_before, win_before, win_after, best_uci, label, opening}]}.
    win_before / win_after are the mover's win%."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("No game found in PGN")
    board = game.board()
    played = list(game.mainline_moves())
    moves = []
    in_book = book is not None
    prev = None
    with Engine() as eng:
        win, best, _ = _position(eng, conn, board, depth, adaptive)      # position before move 1
        for ply, move in enumerate(played, start=1):
            fen_before, san, uci = board.fen(), board.san(move), move.uci()
            before_board = board.copy()
            recapture = prev is not None and board.is_capture(move) and prev.to_square == move.to_square

            # "Only move" check: needs the 2nd-best line, so it is only done for top moves in open positions
            gap = None
            if uci == best and GAP_MIN_WIN <= win <= GAP_MAX_WIN and not recapture and board.legal_moves.count() >= 2:
                d = depth_for(board, depth) if adaptive else depth
                two = _lines(eng, conn, fen_before, d, need=2)
                if len(two) >= 2 and two[0]["move_uci"] == uci:
                    gap = win_pct(two[0]["cp"], two[0]["mate"]) - win_pct(two[1]["cp"], two[1]["mate"])

            board.push(move)
            next_win, next_best, next_lines = _position(eng, conn, board, depth, adaptive)  # reused as the next "before"
            win_after = 100.0 - next_win                     # flip: next_win belongs to the opponent
            sac = is_sacrifice(before_board, move, next_lines[0].get("pv", [])) if next_lines else False

            opening = None
            if in_book:
                opening = book.get(board.epd())
                if opening is None:
                    in_book = False                          # Book only counts as an unbroken run from move 1

            moves.append({"ply": ply, "san": san, "uci": uci, "fen_before": fen_before,
                          "win_before": win, "win_after": win_after, "best_uci": best, "opening": opening,
                          "label": classify(win, win_after, is_best_move=(uci == best),
                                            is_book=opening is not None, gap=gap, sacrifice=sac)})
            win, best, prev = next_win, next_best, move
            if on_progress:
                on_progress(ply, len(played))
    return {"headers": dict(game.headers), "moves": moves}
