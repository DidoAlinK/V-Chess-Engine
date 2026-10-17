"""Unit tests for move classification, Lichess win% formula, and perspective logic."""

import math
import pytest

from backend.classify import classify, win_pct


class TestBoundaryThresholds:
    """Test boundary drop thresholds: exactly 2%, 5%, 10%, 20% and surrounding deltas."""

    def test_exact_2_percent_boundary(self):
        # Exactly 2.0% drop -> Best
        assert classify(50.0, 48.0) == "Best"
        # Slightly under 2.0% drop -> Best
        assert classify(50.0, 48.01) == "Best"
        # Just above 2.0% drop -> Good
        assert classify(50.0, 47.99) == "Good"

    def test_exact_5_percent_boundary(self):
        # Exactly 5.0% drop -> Good
        assert classify(50.0, 45.0) == "Good"
        # Slightly under 5.0% drop -> Good
        assert classify(50.0, 45.01) == "Good"
        # Just above 5.0% drop -> Inaccuracy
        assert classify(50.0, 44.99) == "Inaccuracy"

    def test_exact_10_percent_boundary(self):
        # Exactly 10.0% drop -> Inaccuracy
        assert classify(50.0, 40.0) == "Inaccuracy"
        # Slightly under 10.0% drop -> Inaccuracy
        assert classify(50.0, 40.01) == "Inaccuracy"
        # Just above 10.0% drop -> Mistake
        assert classify(50.0, 39.99) == "Mistake"

    def test_exact_20_percent_boundary(self):
        # Exactly 20.0% drop -> Mistake
        assert classify(50.0, 30.0) == "Mistake"
        # Slightly under 20.0% drop -> Mistake
        assert classify(50.0, 30.01) == "Mistake"
        # Just above 20.0% drop -> Blunder
        assert classify(50.0, 29.99) == "Blunder"

    def test_zero_and_negative_drop(self):
        # 0.0% drop (perfect continuation) -> Best
        assert classify(60.0, 60.0) == "Best"
        # Position improved (e.g. opponent blunder or deep engine line) -> Best
        assert classify(50.0, 65.0) == "Best"

    def test_normalized_probabilities(self):
        # If passed on 0.0-1.0 scale
        assert classify(0.50, 0.48) == "Best"       # 2% drop
        assert classify(0.50, 0.479) == "Good"      # 2.1% drop
        assert classify(0.50, 0.45) == "Good"       # 5% drop
        assert classify(0.50, 0.449) == "Inaccuracy"# 5.1% drop
        assert classify(0.50, 0.40) == "Inaccuracy" # 10% drop
        assert classify(0.50, 0.399) == "Mistake"   # 10.1% drop
        assert classify(0.50, 0.30) == "Mistake"   # 20% drop
        assert classify(0.50, 0.299) == "Blunder"   # 20.1% drop


class TestWinPercentageFormula:
    """Test Lichess win% conversion from centipawns."""

    def test_equal_position(self):
        assert win_pct(0) == pytest.approx(50.0, abs=1e-5)

    def test_known_centipawn_evals(self):
        # win% = 50 + 50 * (2 / (1 + exp(-0.00368208 * 100)) - 1)
        expected_100 = 50.0 + 50.0 * (2.0 / (1.0 + math.exp(-0.368208)) - 1.0)
        assert win_pct(100) == pytest.approx(expected_100, abs=1e-4)
        assert win_pct(100) == pytest.approx(59.1025, abs=0.01)

        expected_minus_100 = 50.0 + 50.0 * (2.0 / (1.0 + math.exp(0.368208)) - 1.0)
        assert win_pct(-100) == pytest.approx(expected_minus_100, abs=1e-4)
        assert win_pct(-100) == pytest.approx(40.8975, abs=0.01)

    def test_eval_symmetry(self):
        # win_pct(cp) + win_pct(-cp) must equal 100%
        for cp in [10, 50, 150, 300, 750, 1500]:
            assert win_pct(cp) + win_pct(-cp) == pytest.approx(100.0, abs=1e-5)

    def test_extreme_centipawns_no_overflow(self):
        assert win_pct(10000) == 100.0
        assert win_pct(-10000) == 0.0
        assert win_pct(float("inf")) == 100.0
        assert win_pct(float("-inf")) == 0.0
        assert win_pct(1000000) == 100.0
        assert win_pct(-1000000) == 0.0

    def test_none_defaults_to_even(self):
        assert win_pct(None) == 50.0


class TestMateScores:
    """Test mate score handling in win_pct and classifications."""

    def test_direct_mate_parameter(self):
        assert win_pct(mate=1) == 100.0
        assert win_pct(mate=3) == 100.0
        assert win_pct(mate=-1) == 0.0
        assert win_pct(mate=-4) == 0.0
        assert win_pct(mate=0) == 100.0

    def test_mate_string_representations(self):
        assert win_pct("+M1") == 100.0
        assert win_pct("#1") == 100.0
        assert win_pct("-M2") == 0.0
        assert win_pct("-#3") == 0.0

    def test_classifying_mate_transitions(self):
        # Mover had mate-in-1 (100% win) and delivered checkmate (100% win) -> Best
        assert classify(win_pct(mate=1), win_pct(mate=0)) == "Best"

        # Mover had mate-in-2 (100% win) but played a blunder dropping into mate against them (0% win)
        wb = win_pct(mate=2)
        wa = win_pct(mate=-1)
        assert wb == 100.0
        assert wa == 0.0
        assert classify(wb, wa) == "Blunder"

        # Mover blundered mate into equal position (100% -> 50% = 50% drop)
        assert classify(win_pct(mate=1), win_pct(0)) == "Blunder"

        # Losing player (-M1, 0% win) finds stalemate trick (50% win) -> Best
        assert classify(win_pct(mate=-1), win_pct(0)) == "Best"


class TestBlackToMovePerspective:
    """Test that evaluations and classifications correctly respect Black-to-move perspective."""

    def test_mover_perspective_sign(self):
        # Rule: Eval is always from the mover's perspective.
        # When Black is to move and Black is winning (+200 cp for Black):
        black_cp = 200
        assert win_pct(black_cp) > 50.0

        # When Black is to move and White is winning (+200 cp for White -> -200 cp for Black):
        white_cp = 200
        black_mover_cp = -white_cp
        assert win_pct(black_mover_cp) < 50.0
        assert win_pct(black_mover_cp) == pytest.approx(100.0 - win_pct(white_cp), abs=1e-5)

    def test_black_move_classifications(self):
        # Black is defending down a pawn (wb = 40%) and plays top engine defense (wa = 40%)
        assert classify(40.0, 40.0) == "Best"

        # Black is winning (wb = 75%) and plays a good move (wa = 71%, drop = 4%)
        assert classify(75.0, 71.0) == "Good"

        # Black is even (wb = 50%) and plays an inaccuracy (wa = 43%, drop = 7%)
        assert classify(50.0, 43.0) == "Inaccuracy"

        # Black has advantage (wb = 65%) and makes a mistake (wa = 50%, drop = 15%)
        assert classify(65.0, 50.0) == "Mistake"

        # Black blunders a rook (wb = 55% -> wa = 20%, drop = 35%)
        assert classify(55.0, 20.0) == "Blunder"

    def test_black_mate_sequences(self):
        # Black has forced mate in 3 from Black's perspective
        wb = win_pct(mate=3)
        assert wb == 100.0

        # Black executes mate-in-2
        wa = win_pct(mate=2)
        assert wa == 100.0
        assert classify(wb, wa) == "Best"

        # White has forced mate against Black (-M2 from Black's perspective)
        black_losing_wb = win_pct(mate=-2)
        assert black_losing_wb == 0.0
