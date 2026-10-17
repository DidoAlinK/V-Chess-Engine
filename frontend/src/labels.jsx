export const LABELS = {
  Brilliant: { c: '#1baca6', s: '!!' }, Great: { c: '#5c8bb0', s: '!' }, Best: { c: '#81b64c', s: '★' },
  Excellent: { c: '#96bc4b', s: '✓' }, Good: { c: '#a3a38a', s: '✓' }, Inaccuracy: { c: '#f7c631', s: '?!' },
  Mistake: { c: '#e58f2a', s: '?' }, Miss: { c: '#ff7769', s: '×' }, Blunder: { c: '#ca3431', s: '??' },
};
export const FLAGGED = ['Inaccuracy', 'Mistake', 'Miss', 'Blunder']; // these get an LLM explanation

export function Chip({ label, big }) {
  const l = LABELS[label];
  if (!l) return null;
  return <span className={big ? 'chip big' : 'chip'} style={{ background: l.c }} title={label}>{l.s}</span>;
}
