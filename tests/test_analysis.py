"""Unit and integration tests for engine analysis wrapper and process lifecycle."""

from pathlib import Path
import chess
import pytest

from backend.analysis import Engine, analyse, get_engine_path


def test_get_engine_path():
    path = get_engine_path()
    assert path is not None
    assert len(path) > 0


def test_engine_context_manager_lifecycle():
    engine_path = get_engine_path()
    with Engine(engine_path) as eng:
        assert eng._engine is not None
        # Verify engine can analyze
        res = eng.analyse(chess.STARTING_FEN, depth=5, multipv=1)
        assert isinstance(res, list)
        assert len(res) == 1
        assert "move_uci" in res[0]
        assert "cp" in res[0]
        assert "mate" in res[0]

    # After exit, engine must be closed and cleaned up
    assert eng._engine is None


def test_analyse_function():
    # Transient analyse call
    res = analyse(chess.STARTING_FEN, depth=5, multipv=1)
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0]["move_uci"] is not None
    assert isinstance(res[0]["cp"], int)
    assert res[0]["mate"] is None


def test_analyse_multipv():
    res = analyse(chess.STARTING_FEN, depth=5, multipv=3)
    assert isinstance(res, list)
    assert len(res) == 3
    for entry in res:
        assert entry["move_uci"] is not None


def test_black_perspective_analysis():
    # Position where it is Black's turn after 1. e4
    black_turn_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    with Engine() as eng:
        res = eng.analyse(black_turn_fen, depth=5, multipv=1)
        assert len(res) == 1
        # cp is from mover's perspective (Black)
        assert isinstance(res[0]["cp"], int)
        # Black is slightly down or equal (~ -10 to -30 cp from Black's perspective)
        assert res[0]["mate"] is None


def test_terminal_position_checkmate():
    # Scholar's mate final position
    mate_fen = "r1bqkb1r/pppp1Qpp/2n5/4p3/2B1n3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
    res = analyse(mate_fen, depth=5, multipv=1)
    assert len(res) == 1
    assert res[0]["move_uci"] is None
    assert res[0]["mate"] == 0
