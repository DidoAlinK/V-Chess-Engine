from backend import db

def test_fen_key_ignores_move_counters():
    a = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    b = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 5 9"
    assert db.fen_key(a) == db.fen_key(b)

def test_eval_cache_roundtrip_and_depth_separation():
    conn = db.connect(":memory:")
    fen = "8/8/8/8/8/8/8/K6k w - - 0 1"
    assert db.get_eval(conn, fen, "stockfish", 12) is None
    db.put_eval(conn, fen, "stockfish", 12, [{"move_uci": "a1a2", "cp": 0, "mate": None}])
    assert db.get_eval(conn, fen, "stockfish", 12)[0]["move_uci"] == "a1a2"
    assert db.get_eval(conn, fen, "stockfish", 18) is None   # a shallow result must not answer a deeper request

def test_add_game_is_idempotent():
    conn = db.connect(":memory:")
    args = dict(source="chesscom", source_id="https://x/1", white="a", black="b", result="1-0", played_at="2026.10.01", pgn="1. e4 *")
    id1, created1 = db.add_game(conn, **args)
    id2, created2 = db.add_game(conn, **args)
    assert (created1, created2) == (True, False) and id1 == id2
    assert len(db.list_games(conn)) == 1

def test_save_moves_marks_done_and_cascade_delete():
    conn = db.connect(":memory:")
    gid, _ = db.add_game(conn, "pgn", "x", "a", "b", "*", None, "1. e4 *")
    move = dict(ply=1, san="e4", uci="e2e4", fen_before="f", win_before=50.0, win_after=49.0, best_uci="e2e4", label="Best")
    db.save_moves(conn, gid, [move])
    game = db.get_game(conn, gid)
    assert game["status"] == "done" and game["moves"][0]["san"] == "e4"
    db.save_moves(conn, gid, [move])                       # saving again replaces, no duplicates
    assert len(db.get_game(conn, gid)["moves"]) == 1
    conn.execute("DELETE FROM games WHERE id=?", (gid,))
    assert conn.execute("SELECT COUNT(*) FROM moves").fetchone()[0] == 0   # foreign key cascade
