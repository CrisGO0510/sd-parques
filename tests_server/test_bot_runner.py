"""Tests unitarios de BotRunner con delay_fn inline (sin threads ni timing real)."""
from __future__ import annotations

import random
import threading
from unittest.mock import MagicMock

from core.entities import Color, GamePhase
from server.bot_runner import BotRunner
from server.session import GameSession, SessionEntry


def _inline_delay(_delay_seconds: float, cb):
    """Reemplazo de threading.Timer: ejecuta el callback inmediatamente."""
    cb()
    return None  # No timer object; cancel() will be skipped via the runner's guard.


def _make_session_with_bot() -> GameSession:
    return GameSession(
        entries=[
            SessionEntry("c1",       "Cris",     Color.RED,  False),
            SessionEntry("bot:blue", "Bot Azul", Color.BLUE, True),
        ],
        rng=random.Random(1),
    )


def _make_server_stub(session: GameSession) -> MagicMock:
    """BotRunner only needs: server.lock, server.session, and broadcast/reset methods.
    Stub minimalista — el server real será probado en tests de integración."""
    server = MagicMock()
    server.lock = threading.RLock()
    server.session = session
    return server


def test_tick_executes_roll_initial_in_setup():
    session = _make_session_with_bot()
    server = _make_server_stub(session)
    runner = BotRunner(
        server=server,
        rng=random.Random(7),
        delay_fn=_inline_delay,
    )
    runner.bind_session(session, epoch=1)
    runner.schedule("bot:blue")
    # SETUP: el bot tiró inicial — el player_index del bot es 1.
    assert 1 in session.game.initial_rolls


def test_tick_discarded_when_epoch_mismatched():
    """Un timer huérfano (epoch del closure ya no coincide con _epoch del
    runner tras un nuevo bind_session) debe descartarse."""
    session = _make_session_with_bot()
    server = _make_server_stub(session)
    # delay_fn que NO dispara (timer queda en cola).
    runner = BotRunner(server=server, rng=random.Random(7), delay_fn=lambda d, cb: None)
    runner.bind_session(session, epoch=1)
    # Simulamos un reset + nueva partida que avanzó el epoch del runner:
    runner.bind_session(session, epoch=2)
    # Disparamos manualmente el tick con epoch viejo (1):
    runner._tick("bot:blue", epoch=1)
    # No debe haber tirado inicial:
    assert session.game.initial_rolls == {}


def test_tick_discarded_when_not_my_turn():
    session = _make_session_with_bot()
    # Forzar a fase ROLLING con turno del humano (c1 / RED en índice 0).
    session.game.turn_order = [0, 1]
    session.game.current_turn_index = 0
    session.game.phase = GamePhase.ROLLING
    session.game.initial_rolls = {0: 12, 1: 6}

    server = _make_server_stub(session)
    runner = BotRunner(server=server, rng=random.Random(7), delay_fn=_inline_delay)
    runner.bind_session(session, epoch=1)
    runner.schedule("bot:blue")
    # El bot tiene un timer agendado pero no es su turno → no debe haber tirado dados.
    assert session.game.pending_dice == []


def test_cancel_all_clears_pending_timers():
    session = _make_session_with_bot()
    server = _make_server_stub(session)
    cancelled = []

    def tracking_delay(_d, cb):
        stub = MagicMock()
        stub.cancel.side_effect = lambda: cancelled.append(True)
        # No invocamos cb (timer "queda pendiente")
        return stub

    runner = BotRunner(server=server, rng=random.Random(7), delay_fn=tracking_delay)
    runner.bind_session(session, epoch=1)
    runner.schedule("bot:blue")
    runner.cancel_all()
    assert cancelled == [True]
