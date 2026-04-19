# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Distributed Colombian Parqués game for 2–4 players (university Distributed Systems final project). Python Flask + Socket.IO server, Quasar/Vue 3 client that also builds an Android APK via Capacitor. Deployed to Render with managed PostgreSQL. Design spec and implementation plan live in `docs/superpowers/specs/` and `docs/superpowers/plans/` — read them before large changes.

## Commands

### Server (Python 3.11, Flask)

Run from the repo root (imports are absolute, e.g. `from server.config import Config`, so you must NOT `cd server` first):

```bash
# One-time DB setup (docker-compose only brings up Postgres)
docker compose up -d

# Install deps into server/.venv
python -m venv server/.venv && server/.venv/bin/pip install -r server/requirements.txt

# Run the dev server (eventlet + Socket.IO on :5000)
server/.venv/bin/python -m server.app

# Tests (pytest discovers server/tests/)
server/.venv/bin/pytest server/tests
server/.venv/bin/pytest server/tests/test_engine.py::test_pairs_keep_turn   # single test
```

`Dockerfile` also runs `python -m server.app` from `/app`, so the package is always addressed as `server.*`.

### Client (Quasar 2 / Vue 3 / Vite)

```bash
cd client
npm install
npm run dev        # quasar dev — hash-mode SPA on the default Quasar port
npm run build      # writes client/dist/spa (consumed by render.yaml and Capacitor)

# Android APK (Capacitor wraps client/dist/spa)
npx quasar build && npx cap sync android && npx cap open android
```

No linter is configured (`npm run lint` is a no-op stub). There are no client-side tests.

### Environment variables

Server reads (see `server/config.py`): `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET`, `CLAUDE_API_KEY`. Client reads (Vite): `VITE_API_URL`, `VITE_SOCKET_URL` — both point to the Render server URL in production (`render.yaml`) and default to `http://localhost:5000` locally (`src/composables/useSocket.js`).

## Architecture

### Server layout — the flow matters

The server is a single Flask app (`server/app.py:create_app`) that mounts REST blueprints **and** registers Socket.IO event handlers by importing their modules for their side effects:

```
server/
  app.py            create_app() — registers blueprints + imports socket modules
  extensions.py     db (SQLAlchemy), socketio (eventlet async_mode, CORS *)
  config.py         env-backed Config class
  routes/           REST blueprints (auth, stats) mounted at /api
  sockets/          Socket.IO handlers — imported for @socketio.on side effects
    lobby.py         join_lobby, select_color, start_game
    game_events.py   roll_dice, move_piece, finish_piece_choice, pass_turn,
                     request_recommendation, disconnect
    sync.py          Berkeley clock-sync responses
  game/             Pure game logic (no Flask / no DB imports)
    constants.py     BOARD_SIZE=68, EXIT_POSITIONS, SAFE_POSITIONS, HOME_ENTRY
    board.py         Board + Piece (state: jail|board|home_stretch|finished)
    engine.py        GameEngine — turn state machine, per-game threading.Lock
    manager.py       game_manager singleton — lobby + active_game + sid↔color maps
  services/         Stateless helpers (auth/JWT, stats, Berkeley, recommendation)
  models/           SQLAlchemy models: User, Game, GamePlayer, GameMove
  tests/            pytest — engine/board unit tests, no DB
```

**Key invariants to preserve:**

- `server.game.*` must not import Flask, SQLAlchemy, or socketio. The engine is testable without an app context (see `server/tests/`). DB writes and event emission live in `server/sockets/` and route handlers.
- The lobby+active game is a **process-wide singleton** (`game_manager` in `server/game/manager.py`). The whole product is designed for one concurrent game — `join_lobby` returns an error if `game_in_progress`. Do not add multi-game routing without a plan update.
- All mutations to `GameEngine` state go through methods that take `self.lock` (`roll_dice`, `execute_move`, `finish_piece_by_choice`, `pass_turn` via `_advance_turn`). If you add a new action, grab the lock.
- `GameEngine.get_movable_pieces` and `services/recommendation.score_moves` simulate moves by calling `board.move_piece`, snapshotting piece state and any captured victims, then reverting. This is not pure — touching `move_piece` means auditing both simulation callers.
- `roll_initial` runs once per game to reorder `player_colors` by the highest opening roll (`phase_initial` gate). Unit tests set `engine.phase_initial = False` to skip it.
- Socket rooms: `"lobby"` during matchmaking, `f"game_{game_id}"` during play. `start_game` moves every player sid from one to the other and persists `Game` + `GamePlayer` rows.
- `services/berkeley.BerkeleySynchronizer` implements the Berkeley clock-sync algorithm (required by the course); `sockets/sync.py` holds a `game_room → synchronizer` dict and handles `sync_response` events.
- `services/recommendation.get_recommendation` is hybrid: heuristic scoring is authoritative (`score_moves`), the LLM (`claude-haiku-4-5-20251001` via `anthropic` SDK) only rewrites the explanation and falls back silently if `CLAUDE_API_KEY` is unset or the call raises.

### Client layout

```
client/src/
  boot/             (empty — no boot files wired in quasar.config.js)
  composables/      useAuth, useSocket (singleton socket), useGame
  stores/           Pinia — userStore (persisted token), gameStore
  pages/            Login, Lobby, Game, Stats, ErrorNotFound
  components/       BoardCanvas, DiceRoller, PlayerInfo, RecommendationPanel
  router/           hash-mode routes; /lobby, /game, /stats require auth
```

The socket is a module-level singleton in `useSocket.js` — call `connect()` after login (token lives in `userStore`) and reuse the same instance across pages. `gameStore.updateFromState` is the single entry point for `game_start` and `board_update` payloads.

### Deploy (Render)

`render.yaml` defines two services + one managed database. The server service runs `python -m server.app` from `server/` (not root — see the `cd server` in `buildCommand`/`startCommand`); this works because `python -m server.app` resolves `server.app` as a top-level package from its own parent, but the local dev invocation from the repo root is what the unit tests and Dockerfile assume. If you refactor imports, verify all three entry points still work.

## Conventions worth knowing

- Spanish is the user-facing language (UI copy, recommendation reasons, spec docs). Code identifiers and comments are English.
- No linter, no formatter, no CI config. Tests are the only automated check — run them before claiming a change is safe.
- Don't commit `.env`, `server/.venv/`, `client/node_modules/`, `client/dist/`, or anything under `.superpowers/` (already gitignored).
