import { mock } from './mock.js';

async function http(path, body) {
  const r = await fetch('/api' + path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}

const real = {
  listGames: () => http('/games'),
  getGame: (id) => http(`/games/${id}`),
  importGame: (b) => http('/games/import', b),
  analyze: (id) => http(`/games/${id}/analyze`, {}),
  job: (id) => http(`/jobs/${id}`),
  explain: (moveId) => http(`/moves/${moveId}/explain`),
  learnNew: (b) => http('/learn/new', b),
  learnMove: (b) => http('/learn/move', b),
};

// `npm run dev:mock` sets VITE_MOCK=1 so the UI runs with no backend.
export const api = import.meta.env.VITE_MOCK === '1' ? mock : real;
