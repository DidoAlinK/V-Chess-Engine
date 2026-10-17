"""Chess engine wrapper around python-chess SimpleEngine with guaranteed process cleanup."""

from contextlib import contextmanager
from pathlib import Path
import shutil
import tomllib
from typing import Generator

import chess
import chess.engine


def get_engine_path(config_path: str | Path | None = None) -> str:
    """Read the UCI engine path from config.toml, or fall back to system PATH."""
    candidates = []
    if config_path:
        candidates.append(Path(config_path))
    candidates.extend([
        Path.cwd() / "config.toml",
        Path(__file__).resolve().parent.parent / "config.toml",
        Path(__file__).resolve().parent / "config.toml",
    ])

    for p in candidates:
        if p.is_file():
            try:
                with open(p, "rb") as f:
                    cfg = tomllib.load(f)
                if "engine" in cfg and isinstance(cfg["engine"], dict) and "path" in cfg["engine"]:
                    return str(cfg["engine"]["path"])
                if "stockfish" in cfg and isinstance(cfg["stockfish"], dict) and "path" in cfg["stockfish"]:
                    return str(cfg["stockfish"]["path"])
                if "engine_path" in cfg:
                    return str(cfg["engine_path"])
                if "path" in cfg:
                    return str(cfg["path"])
            except Exception:
                pass

    sf = shutil.which("stockfish")
    if sf:
        return sf
    return "stockfish"


class Engine:
    """Context manager wrapper around chess.engine.SimpleEngine that ensures process cleanup."""

    def __init__(self, engine_path: str | Path | None = None):
        self.engine_path = str(engine_path or get_engine_path())
        self._engine: chess.engine.SimpleEngine | None = None

    def __enter__(self) -> "Engine":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def start(self) -> None:
        if self._engine is None:
            self._engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)

    def close(self) -> None:
        """Terminate the engine and ensure the underlying process is completely killed."""
        if self._engine is not None:
            engine = self._engine
            self._engine = None

            # Attempt graceful quit
            try:
                engine.quit()
            except Exception:
                pass

            # Close transport
            try:
                engine.close()
            except Exception:
                pass

            # Force kill underlying subprocess if still running
            try:
                if hasattr(engine, "transport") and engine.transport:
                    proc = engine.transport.get_extra_info("subprocess")
                    if proc and proc.poll() is None:
                        proc.kill()
                        proc.wait(timeout=1.0)
            except Exception:
                pass

    def analyse(self, fen: str, depth: int = 12, multipv: int = 1) -> list[dict]:
        """Analyse a position given by FEN at specified depth and multipv.

        Returns a list of dicts: [{"move_uci": str | None, "cp": int | None, "mate": int | None}, ...]
        Scores are always from the mover's perspective.
        """
        self.start()
        assert self._engine is not None

        board = chess.Board(fen)

        # Handle terminal positions (checkmate / stalemate)
        if board.is_checkmate():
            return [{"move_uci": None, "cp": None, "mate": 0}]
        if board.is_stalemate() or board.is_insufficient_material():
            return [{"move_uci": None, "cp": 0, "mate": None}]

        limit = chess.engine.Limit(depth=depth)
        infos = self._engine.analyse(board, limit=limit, multipv=multipv)

        # Ensure infos is always a list
        if isinstance(infos, dict):
            infos = [infos]

        results = []
        for info in infos:
            score = info.get("score")
            pv = info.get("pv")

            move_uci = pv[0].uci() if pv and len(pv) > 0 else None
            cp = None
            mate = None

            if score is not None:
                # Score relative to the mover (side to move in the given position)
                rel_score = score.relative
                if rel_score.is_mate():
                    mate = rel_score.mate()
                else:
                    cp = rel_score.score()

            results.append({
                "move_uci": move_uci,
                "cp": cp,
                "mate": mate,
            })

        return results


@contextmanager
def engine_context(engine_path: str | Path | None = None) -> Generator[Engine, None, None]:
    """Context manager yielding an active Engine instance with guaranteed cleanup."""
    eng = Engine(engine_path=engine_path)
    try:
        eng.start()
        yield eng
    finally:
        eng.close()


def analyse(
    fen: str,
    depth: int = 12,
    multipv: int = 1,
    engine_path: str | Path | None = None,
) -> list[dict]:
    """Analyse a position using a transient engine process that is killed on exit."""
    with Engine(engine_path=engine_path) as eng:
        return eng.analyse(fen, depth=depth, multipv=multipv)
