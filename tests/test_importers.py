from backend import db
from backend.importers import import_pgn_text

TWO_GAMES = """[Event "g1"]
[White "A"]
[Black "B"]
[Result "1-0"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0

[Event "g2"]
[White "C"]
[Black "D"]
[Result "*"]
[Link "https://www.chess.com/game/live/123"]

1. d4 d5 *
"""

def test_import_two_games_then_again_is_idempotent():
    conn = db.connect(":memory:")
    first = import_pgn_text(conn, TWO_GAMES)
    assert [created for _, created in first] == [True, True]
    again = import_pgn_text(conn, TWO_GAMES)
    assert [created for _, created in again] == [False, False]
    assert len(db.list_games(conn)) == 2
    assert db.list_games(conn)[0]["white"] == "C"
