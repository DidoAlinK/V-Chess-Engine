import { useRef, useState } from 'react';
import { Chess } from 'chess.js';
import { api } from './api.js';
import Board from './Board.jsx';

const PRESETS = [1320, 1500, 1800, 2100, 2500, 3190];
const toMove = (u) => ({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] });

export default function Learn() {
  const chess = useRef(new Chess()); // legal-move logic lives in the browser; the server only picks the bot move and judges yours
  const [elo, setElo] = useState(1500);
  const [color, setColor] = useState('w');
  const [gid, setGid] = useState(null);
  const [fen, setFen] = useState(chess.current.fen());
  const [last, setLast] = useState(null);
  const [sel, setSel] = useState(null);
  const [targets, setTargets] = useState([]);
  const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState([]);
  const [err, setErr] = useState('');

  const sync = (m) => { setFen(chess.current.fen()); setLast(m ? [m.from, m.to] : null); };

  const start = async () => {
    try {
      chess.current = new Chess(); setNotes([]); setSel(null); setTargets([]); setErr(''); sync(null);
      const r = await api.learnNew({ elo, color });
      setGid(r.game_id);
      if (r.bot_move) sync(chess.current.move(toMove(r.bot_move)));
    } catch (e) { setErr(String(e)); }
  };

  const click = async (sq) => {
    const c = chess.current;
    if (busy || !gid || c.isGameOver() || c.turn() !== color) return;
    if (sel && targets.includes(sq)) {
      const m = c.move({ from: sel, to: sq, promotion: 'q' }); // auto-queen
      setSel(null); setTargets([]); sync(m); setBusy(true);
      try {
        const r = await api.learnMove({ game_id: gid, uci: m.from + m.to + (m.promotion || '') });
        if (r.flagged) setNotes((n) => [{ san: m.san, text: r.explanation }, ...n]);
        if (r.bot_move) sync(c.move(toMove(r.bot_move)));
      } catch (e) { setErr(String(e)); }
      setBusy(false);
      return;
    }
    const p = c.get(sq);
    if (p && p.color === color) { setSel(sq); setTargets(c.moves({ square: sq, verbose: true }).map((x) => x.to)); }
    else { setSel(null); setTargets([]); }
  };

  const c = chess.current;
  const over = c.isGameOver() ? (c.isCheckmate() ? `Checkmate. ${c.turn() === 'w' ? 'Black' : 'White'} wins.` : 'Draw.') : null;

  return (
    <div className="wrap">
      <div className="col"><Board fen={fen} flipped={color === 'b'} last={last} selected={sel} targets={targets} onSquare={click} /></div>
      <aside className="panel">
        {err && <div className="err">{err}</div>}
        <div className="card">
          <div className="muted">Opponent strength</div>
          <div className="elo">{elo}</div>
          <input type="range" min="1320" max="3190" step="10" value={elo} onChange={(e) => setElo(+e.target.value)} />
          <div className="presets">{PRESETS.map((p) => <button key={p} className={p === elo ? 'on' : ''} onClick={() => setElo(p)}>{p}</button>)}</div>
          <div className="presets">
            <button className={color === 'w' ? 'on' : ''} onClick={() => setColor('w')}>Play White</button>
            <button className={color === 'b' ? 'on' : ''} onClick={() => setColor('b')}>Play Black</button>
          </div>
          <button className="primary" onClick={start}>{gid ? 'New game' : 'Start game'}</button>
          {over && <p className="coach">{over}</p>}
          {busy && <p className="muted">Opponent is thinking…</p>}
        </div>
        <div className="card">
          <div className="muted">Coach</div>
          {notes.length === 0 && <p className="muted">Play a move. I'll speak up when you slip.</p>}
          {notes.map((n, i) => <p key={i} className="coach"><b>{n.san}</b>: {n.text}</p>)}
        </div>
      </aside>
    </div>
  );
}
