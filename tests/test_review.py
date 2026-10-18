from pathlib import Path
import chess
import pytest
from backend import db, review

DATA = Path(__file__).parent / "data"

class FakeEngine:
    """Counts calls. Returns equal positions; the 'best' move is the LAST legal move (never one we play).
    FakeEngine.script maps a fen_key to a list of lines to return instead."""
    calls = 0
    script = {}
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def analyse(self, fen, depth, multipv=1):
        FakeEngine.calls += 1
        scripted = FakeEngine.script.get(db.fen_key(fen))
        if scripted:
            return scripted[:max(1, multipv)]
        legal = [m.uci() for m in chess.Board(fen).legal_moves]
        return [{"move_uci": u, "cp": 0, "mate": None, "pv": [u]} for u in reversed(legal)][:max(1, multipv)]

def test_each_position_analysed_once_and_cache_reuses(monkeypatch):
    monkeypatch.setattr(review, "Engine", FakeEngine)
    pgn = (DATA / "hung_queen.pgn").read_text()
    conn = db.connect(":memory:")
    FakeEngine.calls = 0
    review.review_game(pgn, depth=5, conn=conn)
    assert FakeEngine.calls == 7          # 6 plies -> 7 positions, not 12
    FakeEngine.calls = 0
    review.review_game(pgn, depth=5, conn=conn)
    assert FakeEngine.calls == 0          # everything comes from the cache

def test_numbers_chain_between_moves(monkeypatch):
    monkeypatch.setattr(review, "Engine", FakeEngine)
    moves = review.review_game((DATA / "hung_queen.pgn").read_text(), depth=5)["moves"]
    for a, b in zip(moves, moves[1:]):
        assert a["win_after"] == pytest.approx(100 - b["win_before"])

def test_great_move_when_second_best_is_much_worse(monkeypatch):
    monkeypatch.setattr(review, "Engine", FakeEngine)
    start = db.fen_key(chess.STARTING_FEN)
    def run(second_cp):
        FakeEngine.script = {start: [{"move_uci": "e2e4", "cp": 0, "mate": None, "pv": ["e2e4"]},
                                     {"move_uci": "d2d4", "cp": second_cp, "mate": None, "pv": ["d2d4"]}]}
        return review.review_game('[Event "x"]\n\n1. e4 *\n', depth=5)["moves"][0]["label"]
    try:
        assert run(-150) == "Great"     # alternatives lose ~13% win chance
        assert run(-20) == "Best"
    finally:
        FakeEngine.script = {}

def test_book_is_an_unbroken_run_from_move_one(monkeypatch):
    monkeypatch.setattr(review, "Engine", FakeEngine)
    from backend import book as book_module
    b = book_module.parse_tsv("eco\tname\tpgn\nC20\tKing's Pawn Game\t1. e4 e5\n")
    moves = review.review_game('[Event "x"]\n\n1. e4 e5 2. Nf3 Nc6 *\n', depth=5, book=b)["moves"]
    assert [m["label"] == "Book" for m in moves] == [True, True, False, False]
    assert moves[0]["opening"] == "King's Pawn Game"
    no_book = review.review_game('[Event "x"]\n\n1. e4 e5 *\n', depth=5)["moves"]
    assert all(m["label"] != "Book" for m in no_book)

def test_sacrifice_detection():
    # Bxf7+ Kxf7: a bishop for a pawn is a sacrifice
    board = chess.Board("4k3/5p2/8/8/2B5/8/8/4K3 w - - 0 1")
    assert review.is_sacrifice(board, chess.Move.from_uci("c4f7"), ["e8f7", "e1e2"])
    # Nxe6 dxe6: an even trade is not
    board = chess.Board("4k3/3p4/4n3/8/5N2/8/8/4K3 w - - 0 1")
    assert not review.is_sacrifice(board, chess.Move.from_uci("f4e6"), ["d7e6", "e1e2"])
    # no line known -> never a sacrifice
    assert not review.is_sacrifice(board, chess.Move.from_uci("f4e6"), [])

def test_depth_schedule():
    assert review.depth_for(chess.Board(), 18) == 18                                   # 32 pieces
    assert review.depth_for(chess.Board("8/8/8/4k3/8/8/4P3/4K3 w - - 0 1"), 18) == 40  # 3 pieces
    assert review.depth_for(chess.Board("4k3/pppp4/8/8/8/8/PPPP4/4K3 w - - 0 1"), 18) == 24  # 10 pieces

def test_review_uses_deeper_search_in_endgames(monkeypatch):
    depths = []
    class Recording(FakeEngine):
        def analyse(self, fen, depth, multipv=1):
            depths.append(depth)
            return super().analyse(fen, depth, multipv)
    monkeypatch.setattr(review, "Engine", Recording)
    pgn = '[SetUp "1"]\n[FEN "8/8/8/4k3/8/8/4P3/4K3 w - - 0 1"]\n\n1. Kd2 Kd5 *\n'
    review.review_game(pgn, depth=10)
    assert set(depths) == {32}
    depths.clear()
    review.review_game(pgn, depth=10, adaptive=False)
    assert set(depths) == {10}

# ---- real Stockfish (skipped if the engine is not available) ---------------
@pytest.fixture(scope="module")
def real_engine():
    try:
        with review.Engine() as e:
            e.analyse(chess.STARTING_FEN, 1, 1)
    except Exception as exc:
        pytest.skip(f"Stockfish not available: {exc}")

def labels(name):
    result = review.review_game((DATA / name).read_text(), depth=12)
    return {m["san"]: m["label"] for m in result["moves"]}

def test_hung_queen_is_blunder(real_engine):
    assert labels("hung_queen.pgn")["Qxe5+"] == "Blunder"

def test_black_allows_mate_and_mating_move_is_best(real_engine):
    got = labels("mate_in_one.pgn")
    assert got["Nf6"] == "Blunder"     # Black's perspective
    assert got["Qxf7#"] == "Best"      # checkmate must not break anything
