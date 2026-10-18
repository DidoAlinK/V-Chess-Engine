"""Win% and move labels. All numbers are from the MOVER's point of view."""
import math

# Tunable rules (fitted to a first game; recalibrate as you review more games)
GREAT_GAP = 8.0             # best move beats the 2nd-best by this many win% points -> Great
BRILLIANT_MAX_WIN_BEFORE = 80.0   # no Brilliant when you were already clearly winning
BRILLIANT_MIN_WIN_AFTER = 45.0    # ...and the sacrifice must not leave you worse
MISS_MIN_WIN_BEFORE = 65.0  # you were clearly better...
MISS_MIN_DROP = 10.0        # ...and threw a big part of it away
MISS_MAX_WIN_AFTER = 60.0   # ...so the advantage is mostly gone (88% -> 78% is just a Good move)
MISS_MIN_WIN_AFTER = 35.0   # (if you are simply lost afterwards it is a Blunder, not a Miss)

def win_pct(cp, mate=None):
    """Win chance 0-100 for the side whose score this is (Lichess formula)."""
    if mate is not None:
        return 100.0 if mate > 0 else 0.0      # mate 0 = this side is already checkmated
    if cp is None:
        raise ValueError("need cp or mate")
    cp = max(-1000, min(1000, cp))              # Lichess clamps at +-1000 centipawns
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)

def classify(win_before, win_after, is_best_move=False, *, is_book=False, gap=None, sacrifice=False):
    """win_before: mover's win% before the move (after the engine's best move).
    win_after: mover's win% after the move actually played.
    gap: win% lead of the best move over the 2nd best (None if unknown).
    sacrifice: the move gives up material that is not regained."""
    if is_book:
        return "Book"
    drop = win_before - win_after
    if sacrifice and drop <= 2 and win_before <= BRILLIANT_MAX_WIN_BEFORE and win_after >= BRILLIANT_MIN_WIN_AFTER:
        return "Brilliant"
    if is_best_move:
        if gap is not None and gap >= GREAT_GAP:
            return "Great"
        return "Best"
    if (win_before >= MISS_MIN_WIN_BEFORE and drop >= MISS_MIN_DROP
            and MISS_MIN_WIN_AFTER <= win_after <= MISS_MAX_WIN_AFTER):
        return "Miss"
    if drop <= 2:
        return "Excellent"
    if drop <= 5:
        return "Good"
    if drop <= 10:
        return "Inaccuracy"
    if drop <= 20:
        return "Mistake"
    return "Blunder"
