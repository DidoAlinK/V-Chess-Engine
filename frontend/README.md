# V-Chess frontend

    npm install
    npm run dev:mock   # UI with fake data, no backend needed
    npm run dev        # UI against FastAPI on :8000 (Vite proxies /api)
    npm run build      # outputs dist/

Serve `dist/` from FastAPI (mount it AFTER your API routes):

    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="ui")

## Data contract notes
- `GET /api/games/{id}` -> `{id, white, black, result, status, moves:[{id, ply, san, label, win_before, win_after, best_uci}]}`
- `win_before` / `win_after` are from the MOVER's perspective (0-100). The UI converts to White's side for the bar and graph. `ply` 1 = White's first move.
- `best_uci` is the engine's best move in the position BEFORE the move (only needed for flagged moves).
- `GET /api/jobs/{id}` -> `{status: "running"|"done"|"error", progress, error?}`
- `POST /api/learn/new` -> `{game_id, bot_move|null}`; `POST /api/learn/move` -> `{bot_move|null, flagged, explanation|null}`. Moves are UCI strings (e2e4, e7e8q).
- The browser (chess.js) checks move legality in Learn mode; the backend should still validate.
