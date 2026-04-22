/**
 * Smoke test: two WebSocket clients complete a full parqués lobby → game_started → disconnect → game_over flow.
 *
 * Usage:
 *   node scripts/smoke_two_clients.mjs
 *
 * Exit 0 on success, 1 on failure.
 */

import { spawn } from 'node:child_process';

const PYTHON = '/home/cris/Documents/sistemas-distribuidos/sd-parques/.venv/bin/python';
const SERVER_CWD = '/home/cris/Documents/sistemas-distribuidos/sd-parques';
const TIMEOUT_MS = 15_000;

// ── helpers ──────────────────────────────────────────────────────────────────

/** Log a tagged message to stdout. */
function log(tag, ...args) {
  console.log(`[${tag}]`, ...args);
}

/** Reject with a timeout after ms milliseconds. */
function withTimeout(ms, promise, label) {
  return new Promise((resolve, reject) => {
    const id = setTimeout(() => reject(new Error(`Timeout (${ms}ms): ${label}`)), ms);
    promise.then(
      (v) => { clearTimeout(id); resolve(v); },
      (e) => { clearTimeout(id); reject(e); },
    );
  });
}

/**
 * Scan a readable stream line by line; resolve with the first line matching re.
 * Rejects after timeoutMs.
 */
function waitForLine(readable, re, timeoutMs = 5_000) {
  return new Promise((resolve, reject) => {
    const id = setTimeout(() => reject(new Error(`waitForLine timeout waiting for /${re.source}/`)), timeoutMs);
    let buf = '';
    const onData = (chunk) => {
      buf += chunk.toString('utf8');
      const lines = buf.split('\n');
      buf = lines.pop(); // keep the incomplete tail
      for (const line of lines) {
        process.stderr.write(`  [server] ${line}\n`); // mirror server output
        if (re.test(line)) {
          clearTimeout(id);
          readable.off('data', onData);
          readable.off('error', onErr);
          resolve(line);
        }
      }
    };
    const onErr = (e) => { clearTimeout(id); reject(e); };
    readable.on('data', onData);
    readable.on('error', onErr);
  });
}

/** Open a WebSocket and resolve when it is connected (readyState OPEN). */
function connectWs(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    ws.onopen = () => resolve(ws);
    ws.onerror = (e) => reject(new Error(`WebSocket error connecting to ${url}: ${String(e)}`));
  });
}

/**
 * Send a JSON message on a WebSocket.
 * @param {WebSocket} ws
 * @param {object} msg
 */
function send(ws, msg) {
  ws.send(JSON.stringify(msg));
}

/**
 * Wait for the next message from a WebSocket that satisfies predicate(parsed).
 * Queues messages internally so that earlier messages are not lost.
 *
 * Returns a { ws, nextMsg } pair where nextMsg(pred, label) waits for the next
 * matching message, accumulating mismatches into a queue.
 */
function makeListener(ws, label) {
  /** @type {object[]} */
  const queue = [];
  /** @type {Array<{pred: (m:object)=>boolean, resolve:(m:object)=>void, reject:(e:Error)=>void}>} */
  const waiters = [];

  ws.onmessage = (evt) => {
    let parsed;
    try { parsed = JSON.parse(evt.data); } catch { return; }
    log(label, '←', JSON.stringify(parsed));

    // Try to satisfy any pending waiter
    for (let i = 0; i < waiters.length; i++) {
      if (waiters[i].pred(parsed)) {
        waiters.splice(i, 1)[0].resolve(parsed);
        return;
      }
    }
    // Nobody wants it yet → buffer
    queue.push(parsed);
  };

  /**
   * @param {(m: object) => boolean} pred
   * @param {string} _description
   * @returns {Promise<object>}
   */
  function nextMsg(pred, _description) {
    // Check already-buffered messages first
    const idx = queue.findIndex(pred);
    if (idx !== -1) {
      return Promise.resolve(queue.splice(idx, 1)[0]);
    }
    return new Promise((resolve, reject) => {
      waiters.push({ pred, resolve, reject });
    });
  }

  return { nextMsg };
}

// ── main ─────────────────────────────────────────────────────────────────────

async function main() {
  // ── Step 1: Start the server ──────────────────────────────────────────────
  log('smoke', 'Starting server…');
  const server = spawn(
    PYTHON,
    ['-m', 'server', '--port-tcp', '0', '--port-ws', '0', '--log-level', 'INFO'],
    { cwd: SERVER_CWD, stdio: ['ignore', 'pipe', 'pipe'] },
  );

  server.on('error', (e) => { throw new Error(`Failed to spawn server: ${e.message}`); });

  // Mirror stderr output as it arrives (waitForLine also reads from it)
  const combined = server.stderr; // server writes INFO logs to stderr via logging module

  // Also forward stdout just in case
  server.stdout.on('data', (chunk) => process.stderr.write(`  [server/out] ${chunk}`));

  // ── Step 2: Capture WS port ───────────────────────────────────────────────
  const portLine = await withTimeout(
    5_000,
    waitForLine(combined, /WS listener on [\d.]+:(\d+)/),
    'waiting for "WS listener on" line',
  );
  const portMatch = portLine.match(/:(\d+)\s*$/);
  if (!portMatch) throw new Error(`Could not parse port from: ${portLine}`);
  const wsPort = Number(portMatch[1]);
  log('smoke', `Server WS port: ${wsPort}`);

  // ── Step 3: Connect two clients ───────────────────────────────────────────
  const wsUrl = `ws://127.0.0.1:${wsPort}`;
  log('smoke', `Connecting Alice and Bob to ${wsUrl}…`);

  const [wsA, wsB] = await Promise.all([connectWs(wsUrl), connectWs(wsUrl)]);
  log('smoke', 'Both clients connected');

  const listenerA = makeListener(wsA, 'Alice');
  const listenerB = makeListener(wsB, 'Bob');

  // ── Step 4: Lobby flow ────────────────────────────────────────────────────

  // 4a. Alice joins
  send(wsA, { type: 'join', username: 'Alice' });
  const welcomeA = await withTimeout(
    TIMEOUT_MS,
    listenerA.nextMsg((m) => m.type === 'welcome', 'welcome for Alice'),
    'Alice: welcome',
  );
  if (!welcomeA.is_host) throw new Error(`Expected Alice to be host, got: ${JSON.stringify(welcomeA)}`);
  log('smoke', `Alice welcome: is_host=${welcomeA.is_host} ✓`);

  // 4b. Bob joins
  send(wsB, { type: 'join', username: 'Bob' });
  const welcomeB = await withTimeout(
    TIMEOUT_MS,
    listenerB.nextMsg((m) => m.type === 'welcome', 'welcome for Bob'),
    'Bob: welcome',
  );
  if (welcomeB.is_host) throw new Error(`Expected Bob NOT to be host, got: ${JSON.stringify(welcomeB)}`);
  log('smoke', `Bob welcome: is_host=${welcomeB.is_host} ✓`);

  // 4c. Select colors
  send(wsA, { type: 'select_color', color: 'red' });
  send(wsB, { type: 'select_color', color: 'blue' });

  // 4d. Both wait for lobby_update with 2 players that have colors
  const lobbyUpdateA = await withTimeout(
    TIMEOUT_MS,
    listenerA.nextMsg(
      (m) => m.type === 'lobby_update' && m.players.length === 2 && m.players.every((p) => p.color !== null),
      'Alice: lobby_update with 2 colored players',
    ),
    'Alice: lobby_update 2 players',
  );
  log('smoke', `Alice lobby_update: ${JSON.stringify(lobbyUpdateA.players)} ✓`);

  const lobbyUpdateB = await withTimeout(
    TIMEOUT_MS,
    listenerB.nextMsg(
      (m) => m.type === 'lobby_update' && m.players.length === 2 && m.players.every((p) => p.color !== null),
      'Bob: lobby_update with 2 colored players',
    ),
    'Bob: lobby_update 2 players',
  );
  log('smoke', `Bob lobby_update: ${JSON.stringify(lobbyUpdateB.players)} ✓`);

  // 4e. Alice starts the game
  send(wsA, { type: 'start_game' });

  // 4f. Both expect game_started
  const [gameStartedA, gameStartedB] = await Promise.all([
    withTimeout(
      TIMEOUT_MS,
      listenerA.nextMsg((m) => m.type === 'game_started', 'Alice: game_started'),
      'Alice: game_started',
    ),
    withTimeout(
      TIMEOUT_MS,
      listenerB.nextMsg((m) => m.type === 'game_started', 'Bob: game_started'),
      'Bob: game_started',
    ),
  ]);
  log('smoke', `game_started received by both clients ✓`);
  log('smoke', `  Alice: ${JSON.stringify(gameStartedA)}`);
  log('smoke', `  Bob:   ${JSON.stringify(gameStartedB)}`);

  // ── Step 5: Bob disconnects → Alice wins ──────────────────────────────────
  log('smoke', 'Bob closes socket…');
  wsB.close();

  const gameOver = await withTimeout(
    TIMEOUT_MS,
    listenerA.nextMsg((m) => m.type === 'game_over', 'Alice: game_over'),
    'Alice: game_over',
  );
  log('smoke', `game_over: ${JSON.stringify(gameOver)} ✓`);
  if (gameOver.winner_username !== 'Alice') {
    throw new Error(`Expected winner Alice, got: ${gameOver.winner_username}`);
  }
  log('smoke', `winner_username = "${gameOver.winner_username}" ✓`);

  // ── Cleanup ───────────────────────────────────────────────────────────────
  wsA.close();
  server.kill('SIGTERM');

  // Give server a moment to flush
  await new Promise((r) => setTimeout(r, 300));

  console.log('\n✅ smoke passed');
  process.exit(0);
}

main().catch((e) => {
  console.error('\n❌ smoke FAILED:', e.message);
  process.exit(1);
});
