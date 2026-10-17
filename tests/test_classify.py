import pytest
from backend.classify import classify, win_pct

@pytest.mark.parametrize("drop,label", [
    (0.0, "Best"), (0.5, "Best"), (0.51, "Excellent"), (2.0, "Excellent"), (2.01, "Good"),
    (5.0, "Good"), (5.01, "Inaccuracy"), (10.0, "Inaccuracy"), (10.01, "Mistake"),
    (20.0, "Mistake"), (20.01, "Blunder"), (60.0, "Blunder"), (-3.0, "Best"),
])
def test_thresholds(drop, label):
    assert classify(100.0, 100.0 - drop) == label

def test_engine_top_move_is_always_best():
    assert classify(60.0, 57.0, is_best_move=True) == "Best"

def test_win_pct_basics():
    assert win_pct(0) == pytest.approx(50.0)
    assert win_pct(300) > 70
    assert win_pct(-300) < 30
    assert win_pct(200) + win_pct(-200) == pytest.approx(100.0)

def test_win_pct_extremes_do_not_overflow():
    assert 97 < win_pct(10**7) <= 100      # clamped at +-1000 cp like Lichess, about 97.5%
    assert 0 <= win_pct(-10**7) < 3

def test_mate_scores():
    assert win_pct(None, mate=3) == 100.0
    assert win_pct(None, mate=-2) == 0.0
    assert win_pct(None, mate=0) == 0.0   # already checkmated

def test_perspective_flip_example():
    # Mover is at 50%, plays a move after which the opponent stands at 90% => mover at 10%.
    assert classify(50.0, 100.0 - 90.0) == "Blunder"
