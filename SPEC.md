# ChessReview spec
Local chess review app. Python 3.11, FastAPI, SQLite, python-chess, Stockfish (UCI), Ollama, React+Vite.
Rules: win% uses the Lichess formula. Eval is always from the mover's perspective.
Thresholds (drop in win% = win_before - win_after):
- drop <= 2%: Best
- 2% < drop <= 5%: Good
- 5% < drop <= 10%: Inaccuracy
- 10% < drop <= 20%: Mistake
- drop > 20%: Blunder
LLM never receives a bare FEN; it receives a structured fact bundle only.
One milestone at a time. Every milestone ships with pytest tests. Do not modify files outside the milestone scope.