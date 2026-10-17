import { Chess } from 'chess.js';

const SAN = 'e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d4 exd4 cxd4 Bb4+ Nc3 Nxe4 O-O Bxc3 d5 Bf6 Re1 Ne7 Rxe4 d6 Bg5 Bxg5 Nxg5 O-O Nxh7 Kxh7 Qh5+ Kg8 Rh4 f5'.split(' ');
const LABEL = ['Best','Best','Best','Best','Best','Excellent','Best','Best','Great','Best','Best','Best','Good','Excellent','Brilliant','Mistake','Best','Inaccuracy','Best','Good','Best','Inaccuracy','Great','Mistake','Best','Blunder','Best','Good','Best','Good','Great','Blunder'];
const W = [50,54,52,55,52,56,53,56,53,58,54,58,52,56,50,60,70,71,77,78,77,80,84,86,91,91,96,96,95,96,95,97,99]; // White win% after each ply (illustrative)
const BEST = { 16: 'e4c3', 18: 'c3b2', 22: 'h8f8', 24: 'f6e5', 26: 'h7h6', 32: 'g7g6' };
const wait = (ms = 350) => new Promise((r) => setTimeout(r, ms));

const moves = SAN.map((san, i) => {
  const ply = i + 1, mover = (v) => (ply % 2 ? v : 100 - v); // win% is from the MOVER's perspective
  return { id: ply, ply, san, label: LABEL[i], win_before: mover(W[i]), win_after: mover(W[ply]), best_uci: BEST[ply] };
});

let chess = new Chess();
const botMove = () => {
  if (chess.isGameOver()) return null;
  const all = chess.moves({ verbose: true }), m = all[Math.floor(Math.random() * all.length)];
  chess.move(m);
  return m.from + m.to + (m.promotion || '');
};

export const mock = {
  listGames: async () => [{ id: 1, white: 'You', black: 'Opponent', result: '1-0', source: 'mock', status: 'done' }],
  getGame: async () => ({ id: 1, white: 'You', black: 'Opponent', result: '1-0', status: 'done', moves }),
  importGame: async () => ({ id: 1 }),
  analyze: async () => ({ job_id: 1 }),
  job: async () => ({ status: 'done', progress: 100 }),
  explain: async () => { await wait(700); return { text: 'This move gave up ground the engine had already shown you could hold. Before moving, ask: what does my opponent threaten after this? Check every capture and check first.' }; },
  learnNew: async ({ color }) => { chess = new Chess(); await wait(); return { game_id: 1, bot_move: color === 'b' ? botMove() : null }; },
  learnMove: async ({ uci }) => {
    chess.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci[4] });
    await wait();
    const flagged = Math.random() < 0.3;
    return { flagged, explanation: flagged ? 'That loosens your position. Ask first: which of my pieces are undefended after this move, and what can the opponent capture or check?' : null, bot_move: botMove() };
  },
};
