import pytest
from backend.classify import classify, win_pct

# win_before = 60 keeps us below the Miss/Brilliant zones, so only the drop decides
@pytest.mark.parametrize("drop,label", [
    (0.0, "Excellent"), (0.11, "Excellent"), (0.5, "Excellent"), (2.0, "Excellent"), (2.01, "Good"),
    (5.0, "Good"), (5.01, "Inaccuracy"), (10.0, "Inaccuracy"), (10.01, "Mistake"),
    (20.0, "Mistake"), (20.01, "Blunder"), (60.0, "Blunder"), (-3.0, "Excellent"),
])
def test_thresholds(drop, label):
    assert classify(60.0, 60.0 - drop) == label

def test_engine_top_move_is_always_best():
    assert classify(60.0, 57.0, is_best_move=True) == "Best"
    assert classify(50.0, 50.0, is_best_move=True) == "Best"

def test_non_top_move_with_equal_eval_is_excellent_not_best():
    assert classify(95.0, 95.0, is_best_move=False) == "Excellent"

def test_book_wins_over_everything():
    assert classify(50.0, 10.0, is_book=True) == "Book"

def test_great_needs_top_move_and_big_gap():
    assert classify(50.0, 50.0, True, gap=9.0) == "Great"
    assert classify(50.0, 50.0, True, gap=5.0) == "Best"
    assert classify(50.0, 50.0, True, gap=None) == "Best"
    assert classify(50.0, 45.0, False, gap=30.0) == "Good"      # gap only matters for the top move

def test_brilliant_needs_sacrifice_near_top_and_not_already_winning():
    assert classify(50.0, 49.0, False, sacrifice=True) == "Brilliant"
    assert classify(50.0, 41.0, False, sacrifice=True) == "Inaccuracy"   # sacrifice that costs 9% is just a bad move
    assert classify(90.0, 90.0, True, sacrifice=True) == "Best"          # already winning

def test_miss_is_a_big_drop_from_a_clearly_better_position():
    assert classify(88.0, 46.0) == "Miss"          # winning, threw most of it away
    assert classify(54.0, 12.0) == "Blunder"       # was only slightly better
    assert classify(90.0, 5.0) == "Blunder"        # ended up simply lost
    assert classify(80.0, 72.0) == "Inaccuracy"    # drop too small for a Miss
    assert classify(88.0, 70.0) == "Mistake"       # still clearly better afterwards: not a Miss
    assert classify(88.0, 78.0) == "Inaccuracy"

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
