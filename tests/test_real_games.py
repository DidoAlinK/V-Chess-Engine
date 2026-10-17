import chess
import pytest
from backend.analysis import analyse
from backend.classify import win_pct, classify

DEPTH = 12

def label_moves(sans):
    """Return [(san, label)] using the mover's-perspective win% before and after each move."""
    board, out = chess.Board(), []
    for san in sans:
        move = board.parse_san(san)
        before = analyse(board.fen(), DEPTH, 1)[0]
        wb = win_pct(before["cp"], before["mate"])
        board.push(move)
        after = analyse(board.fen(), DEPTH, 1)[0]      # side to move is now the opponent
        wa = 100 - win_pct(after["cp"], after["mate"])  # flip back to the mover's view
        out.append((san, classify(wb, wa)))
    return out

@pytest.fixture(scope="module")
def stockfish_available():
    try:
        analyse(chess.STARTING_FEN, 1, 1)
    except Exception as e:
        pytest.skip(f"Stockfish not available: {e}")

def test_hung_queen_is_blunder(stockfish_available):
    labels = dict(label_moves("e4 e5 Qh5 Nc6 Qxe5 Nxe5".split()))
    assert labels["Qxe5"] == "Blunder"

def test_black_allows_mate(stockfish_available):
    labels = dict(label_moves("e4 e5 Qh5 Nc6 Bc4 Nf6 Qxf7#".split()))
    assert labels["Nf6"] == "Blunder"      # Black-side perspective
    assert labels["Qxf7#"] == "Best"       # terminal position must not break