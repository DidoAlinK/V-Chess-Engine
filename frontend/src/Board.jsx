import { Chess } from 'chess.js';
import { Chip } from './labels.jsx';
const FILES = 'abcdefgh';

// Props: fen, flipped, last=[from,to], arrow=[from,to], selected, targets=[squares], onSquare(sq), badge={square,label}
export default function Board({ fen, flipped = false, last, arrow, selected, targets = [], onSquare, badge }) {
  const pos = new Chess(fen).board(); // pos[0] is rank 8
  const xy = (sq) => { // square -> centre point in a 100x100 space (for the arrow)
    let f = FILES.indexOf(sq[0]), r = +sq[1] - 1;
    if (flipped) { f = 7 - f; r = 7 - r; }
    return [(f + 0.5) * 12.5, (7 - r + 0.5) * 12.5];
  };

  const cells = [];
  for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) {
    const f = flipped ? 7 - j : j, r = flipped ? i : 7 - i; // file / rank index of this screen cell
    const sq = FILES[f] + (r + 1), p = pos[7 - r][f];
    const cls = ['sq', (f + r) % 2 ? 'l' : 'd'];
    if (last?.includes(sq) || selected === sq) cls.push('hl');
    if (targets.includes(sq)) cls.push('tgt', p ? 'cap' : '');
    cells.push(
      <div key={sq} className={cls.join(' ')} onClick={() => onSquare?.(sq)}>
        {j === 0 && <span className="coord r">{r + 1}</span>}
        {i === 7 && <span className="coord f">{FILES[f]}</span>}
        {p && <img src={`/pieces/${p.color}${p.type.toUpperCase()}.svg`} alt="" draggable={false} />}
        {badge?.square === sq && <span className="badge"><Chip label={badge.label} big /></span>}
      </div>
    );
  }

  let ar = null;
  if (arrow) {
    const [x1, y1] = xy(arrow[0]), [x2, y2] = xy(arrow[1]);
    ar = (
      <svg className="arrow" viewBox="0 0 100 100">
        <defs><marker id="ah" markerWidth="3" markerHeight="3" refX="1.4" refY="1.5" orient="auto"><path d="M0,0 L3,1.5 L0,3 z" fill="#81b64c" /></marker></defs>
        <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#81b64c" strokeWidth="2.2" strokeOpacity=".9" markerEnd="url(#ah)" />
      </svg>
    );
  }
  return <div className="board">{cells}{ar}</div>;
}
