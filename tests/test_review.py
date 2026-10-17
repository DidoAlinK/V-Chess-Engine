from pathlib import Path
import chess
import pytest
from backend import db, review

DATA = Path(__file__).parent / "data"

class FakeEngine:
    """Counts calls. Always says 'first legal move, equal position'."""
    calls = 0
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def analyse(self, fen, depth, multipv=1):
        FakeEngine.calls += 1
        move = next(iter(chess.Board(fen).legal_moves)).uci()
        return [{"move_uci": move, "cp": 0, "mate": None}]

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
