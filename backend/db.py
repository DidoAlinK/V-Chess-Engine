"""SQLite storage. One file: data/chess.db (created automatically)."""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chess.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
  id INTEGER PRIMARY KEY,
  source TEXT NOT NULL,
  source_id TEXT,
  white TEXT, black TEXT, result TEXT, played_at TEXT,
  pgn TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'imported',
  UNIQUE(source, source_id)
);
CREATE TABLE IF NOT EXISTS moves (
  id INTEGER PRIMARY KEY,
  game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  ply INTEGER NOT NULL,
  san TEXT, uci TEXT, fen_before TEXT,
  win_before REAL, win_after REAL,
  best_uci TEXT, pv TEXT, label TEXT,
  UNIQUE(game_id, ply)
);
CREATE TABLE IF NOT EXISTS evals (
  fen_key TEXT NOT NULL,
  engine TEXT NOT NULL,
  depth INTEGER NOT NULL,
  lines_json TEXT NOT NULL,
  PRIMARY KEY (fen_key, engine, depth)
);
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY,
  game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'queued',
  progress INTEGER NOT NULL DEFAULT 0,
  error TEXT
);
CREATE TABLE IF NOT EXISTS explanations (
  move_id INTEGER PRIMARY KEY REFERENCES moves(id) ON DELETE CASCADE,
  model TEXT, text TEXT
);
"""

def connect(path=DB_PATH):
    """Open (and create if needed) the database. Use ':memory:' in tests.
    Each thread should call connect() for its own connection."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")   # SQLite ignores foreign keys unless you ask
    conn.execute("PRAGMA journal_mode = WAL")  # lets one writer and readers work together
    conn.executescript(SCHEMA)
    return conn

# ---- eval cache -------------------------------------------------------------
def fen_key(fen):
    """Keep only pieces, turn, castling, en passant. Drops the move counters so
    the same position reached by a different move order hits the same cache row."""
    return " ".join(fen.split()[:4])

def get_eval(conn, fen, engine, depth):
    row = conn.execute("SELECT lines_json FROM evals WHERE fen_key=? AND engine=? AND depth=?",
                       (fen_key(fen), engine, depth)).fetchone()
    return json.loads(row["lines_json"]) if row else None

def put_eval(conn, fen, engine, depth, lines):
    conn.execute("INSERT OR REPLACE INTO evals(fen_key, engine, depth, lines_json) VALUES (?,?,?,?)",
                 (fen_key(fen), engine, depth, json.dumps(lines)))
    conn.commit()

# ---- games and moves --------------------------------------------------------
def add_game(conn, source, source_id, white, black, result, played_at, pgn):
    """Insert a game. Returns (game_id, created). Importing twice is safe."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO games(source, source_id, white, black, result, played_at, pgn) VALUES (?,?,?,?,?,?,?)",
        (source, source_id, white, black, result, played_at, pgn))
    conn.commit()
    if cur.rowcount:
        return cur.lastrowid, True
    row = conn.execute("SELECT id FROM games WHERE source=? AND source_id=?", (source, source_id)).fetchone()
    return row["id"], False

def list_games(conn):
    rows = conn.execute("SELECT id, source, white, black, result, played_at, status FROM games ORDER BY id DESC")
    return [dict(r) for r in rows]

def get_game(conn, game_id):
    g = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
    if g is None:
        return None
    game = dict(g)
    rows = conn.execute("SELECT * FROM moves WHERE game_id=? ORDER BY ply", (game_id,))
    game["moves"] = [dict(r) for r in rows]
    return game

def save_moves(conn, game_id, moves):
    """Replace all moves of a game with the reviewed ones and mark it done."""
    with conn:  # one transaction: all or nothing
        conn.execute("DELETE FROM moves WHERE game_id=?", (game_id,))
        conn.executemany(
            "INSERT INTO moves(game_id, ply, san, uci, fen_before, win_before, win_after, best_uci, label) VALUES (?,?,?,?,?,?,?,?,?)",
            [(game_id, m["ply"], m["san"], m["uci"], m["fen_before"], m["win_before"], m["win_after"], m["best_uci"], m["label"])
             for m in moves])
        conn.execute("UPDATE games SET status='done' WHERE id=?", (game_id,))
