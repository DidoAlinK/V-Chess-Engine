import { useEffect, useMemo, useState } from 'react';
import { Chess } from 'chess.js';
import { api } from './api.js';
import Board from './Board.jsx';
import { Chip, FLAGGED, LABELS } from './labels.jsx';

// The API sends win% from the MOVER's side. The eval bar and graph need White's side.
const whiteWin = (m, key) => (m.ply % 2 ? m[key] : 100 - m[key]);

export default function Review() {
  const [games, setGames] = useState([]);
  const [game, setGame] = useState(null);
  const [ply, setPly] = useState(0);
  const [showBest, setShowBest] = useState(false);
  const [expl, setExpl] = useState({});
  const [progress, setProgress] = useState(null);
  const [err, setErr] = useState('');

  const load = (id) => api.getGame(id).then((g) => { setGame(g); setPly(0); setExpl({}); }).catch((e) => setErr(String(e)));
  useEffect(() => { api.listGames().then((l) => { setGames(l); if (l[0]) load(l[0].id); }).catch((e) => setErr(String(e))); }, []);

  const moves = game?.moves ?? [];
  const done = game?.status === 'done';

  // Replay SANs once to get a FEN and last-move squares for every ply.
  const { fens, lasts } = useMemo(() => {
    const c = new Chess(), fens = [c.fen()], lasts = [null];
    for (const m of game?.moves ?? []) { const mv = c.move(m.san); fens.push(c.fen()); lasts.push([mv.from, mv.to]); }
    return { fens, lasts };
  }, [game]);

  const cur = ply > 0 ? moves[ply - 1] : null;
  const flagged = cur && FLAGGED.includes(cur.label);

  const bestSan = useMemo(() => {
    if (!cur?.best_uci) return null;
    try { return new Chess(fens[ply - 1]).move({ from: cur.best_uci.slice(0, 2), to: cur.best_uci.slice(2, 4), promotion: cur.best_uci[4] }).san; }
    catch { return cur.best_uci; }
  }, [ply, game]);

  // Ask the coach (LLM) only for flagged moves, once per move.
  useEffect(() => {
    setShowBest(false);
    if (!flagged || expl[cur.id]) return;
    api.explain(cur.id)
      .then((r) => setExpl((e) => ({ ...e, [cur.id]: r.text })))
      .catch(() => setExpl((e) => ({ ...e, [cur.id]: 'Explanation unavailable. Is Ollama running?' })));
  }, [ply, game]);

  useEffect(() => {
    const h = (e) => {
      if (e.key === 'ArrowLeft') setPly((p) => Math.max(0, p - 1));
      if (e.key === 'ArrowRight') setPly((p) => Math.min(moves.length, p + 1));
      if (e.key === 'Home') setPly(0);
      if (e.key === 'End') setPly(moves.length);
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [moves.length]);

  const analyze = async () => {
    try {
      const { job_id } = await api.analyze(game.id);
      setProgress(0);
      const t = setInterval(async () => {
        const j = await api.job(job_id);
        setProgress(j.progress);
        if (j.status === 'done' || j.status === 'error') {
          clearInterval(t); setProgress(null);
          if (j.status === 'error') setErr(j.error || 'Analysis failed'); else load(game.id);
        }
      }, 1000);
    } catch (e) { setErr(String(e)); }
  };

  const series = [50, ...moves.map((m) => (done ? whiteWin(m, 'win_after') : 50))];
  const curWin = series[ply] ?? 50;
  const W = 400, H = 70, n = Math.max(1, moves.length);
  const px = (i) => (i / n) * W, py = (v) => H - (v / 100) * H;
  const pts = series.map((v, i) => `${px(i)},${py(v)}`).join(' ');

  const best = showBest && flagged && cur.best_uci;
  const shownFen = best ? fens[ply - 1] : fens[ply];
  const shownLast = best ? lasts[ply - 1] : lasts[ply];
  const count = (white, lab) => moves.filter((m) => !!(m.ply % 2) === white && m.label === lab).length;
  const rows = []; for (let i = 0; i < moves.length; i += 2) rows.push(i);

  return (
    <div className="wrap">
      <div className="col">
        <div className="boardwrap">
          <div className="evalbar" title={`${curWin.toFixed(0)}% White`}><div className="w" style={{ height: `${curWin}%` }} /></div>
          <Board fen={shownFen ?? fens[0]} last={shownLast} arrow={best ? [cur.best_uci.slice(0, 2), cur.best_uci.slice(2, 4)] : null}
                 badge={!best && cur && lasts[ply] ? { square: lasts[ply][1], label: cur.label } : null} />
        </div>
        <div className="ctrls">
          <button onClick={() => setPly(0)}>⏮</button><button onClick={() => setPly(Math.max(0, ply - 1))}>◀</button>
          <button onClick={() => setPly(Math.min(moves.length, ply + 1))}>▶</button><button onClick={() => setPly(moves.length)}>⏭</button>
        </div>
        {done && (
          <svg className="graph" viewBox={`0 0 ${W} ${H}`} onClick={(e) => { const r = e.currentTarget.getBoundingClientRect(); setPly(Math.round(((e.clientX - r.left) / r.width) * n)); }}>
            <polygon points={`0,${H} ${pts} ${W},${H}`} fill="#f1ebe0" opacity=".92" />
            <line x1="0" x2={W} y1={H / 2} y2={H / 2} stroke="#77512f" strokeDasharray="3 3" />
            <polyline points={pts} fill="none" stroke="#c6a672" strokeWidth="1.5" />
            <line x1={px(ply)} x2={px(ply)} y1="0" y2={H} stroke="#ffdd33" strokeWidth="1.5" />
          </svg>
        )}
      </div>

      <aside className="panel">
        {err && <div className="err">{err}</div>}
        <select value={game?.id ?? ''} onChange={(e) => load(+e.target.value)}>
          {games.map((g) => <option key={g.id} value={g.id}>{g.white} vs {g.black} · {g.result}</option>)}
        </select>
        {game && !done && (progress === null
          ? <button className="primary" onClick={analyze}>Analyze game</button>
          : <div className="prog"><div style={{ width: `${progress}%` }} /></div>)}

        <div className="card">
          {cur ? (
            <>
              <div className="mvhead"><Chip label={cur.label} big /> <b>{Math.ceil(ply / 2)}{ply % 2 ? '.' : '...'} {cur.san}</b> <span className="muted">{cur.label}</span></div>
              {flagged && (
                <>
                  <div className="muted">Best was <b>{bestSan}</b> <button className="link" onClick={() => setShowBest(!showBest)}>{showBest ? 'hide' : 'show'}</button></div>
                  <p className="coach">{expl[cur.id] ?? 'Coach is thinking…'}</p>
                </>
              )}
            </>
          ) : <span className="muted">Use ← → or click a move.</span>}
        </div>

        {done && (
          <table className="sum"><thead><tr><th></th><th>White</th><th>Black</th></tr></thead><tbody>
            {Object.keys(LABELS).map((l) => (
              <tr key={l}><td><Chip label={l} /> {l}</td><td>{count(true, l)}</td><td>{count(false, l)}</td></tr>
            ))}
          </tbody></table>
        )}

        <div className="moves">
          {rows.map((i) => (
            <div className="mv" key={i}>
              <span className="no">{i / 2 + 1}.</span>
              {[i, i + 1].map((k) => moves[k] && (
                <button key={k} className={ply === k + 1 ? 'on' : ''} onClick={() => setPly(k + 1)}>{moves[k].san} <Chip label={moves[k].label} /></button>
              ))}
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
