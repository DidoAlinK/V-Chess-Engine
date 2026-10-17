"""Move quality classification and win percentage conversion using Lichess formula."""

import math
from typing import Any


def win_pct(cp: Any = None, mate: int | None = None) -> float:
    """Calculate winning percentage (0.0 to 100.0) from centipawns or mate.

    Uses the empirical Lichess logistic formula:
        win% = 50 + 50 * (2 / (1 + exp(-0.00368208 * cp)) - 1)

    Eval is always from the mover's perspective.
    """
    # Direct mate parameter
    if mate is not None:
        if mate > 0:
            return 100.0
        elif mate < 0:
            return 0.0
        else:
            return 100.0

    # Support python-chess PovScore / Score objects
    if hasattr(cp, "is_mate") and callable(cp.is_mate):
        if cp.is_mate():
            m = cp.mate()
            if m is not None:
                return 100.0 if m >= 0 else 0.0
            return 100.0
        cp = cp.score()

    # None defaults to equal chances (50.0)
    if cp is None:
        return 50.0

    # Parse string representations like "+M3", "-M1", "#1", or numeric strings
    if isinstance(cp, str):
        s = cp.strip()
        if s.startswith("+M") or s.startswith("#") or s.startswith("M"):
            return 100.0
        if s.startswith("-M") or s.startswith("-#"):
            return 0.0
        try:
            cp = float(s)
        except ValueError:
            return 50.0

    # Infinities or engine mate score bounds (e.g. >= 10000 or <= -10000)
    if cp == float("inf") or cp >= 9000:
        return 100.0
    if cp == float("-inf") or cp <= -9000:
        return 0.0

    # Guard against overflow in math.exp
    exp_arg = -0.00368208 * float(cp)
    if exp_arg > 700.0:
        return 0.0
    if exp_arg < -700.0:
        return 100.0

    return 50.0 + 50.0 * (2.0 / (1.0 + math.exp(exp_arg)) - 1.0)


def classify(win_before: float, win_after: float) -> str:
    """Classify a move based on drop in win percentage (from mover's perspective).

    drop = win_before - win_after

    Thresholds:
      drop <= 2%  -> "Best"
      drop <= 5%  -> "Good"
      drop <= 10% -> "Inaccuracy"
      drop <= 20% -> "Mistake"
      drop > 20%  -> "Blunder"
    """
    wb = float(win_before)
    wa = float(win_after)

    # If inputs were provided as 0.0-1.0 probabilities, normalize to 0.0-100.0
    if 0.0 <= wb <= 1.0 and 0.0 <= wa <= 1.0 and (wb > 0 or wa > 0):
        wb *= 100.0
        wa *= 100.0

    drop = round(wb - wa, 6)

    if drop <= 2.0:
        return "Best"
    elif drop <= 5.0:
        return "Good"
    elif drop <= 10.0:
        return "Inaccuracy"
    elif drop <= 20.0:
        return "Mistake"
    else:
        return "Blunder"
