import { useQuasar } from 'quasar';
import { useServerProtocol } from 'src/composables/useServerProtocol';
import { useGameStore } from 'src/stores/game';
import { useLobbyStore } from 'src/stores/lobby';
import { ServerEventType } from 'src/types/protocol';

/**
 * Registers server-event handlers that update application state
 * (stores + notifications). Call once from a component that never
 * unmounts during navigation — typically `MainLayout.vue`.
 *
 * Why here and not in pages: the server emits `game_started` followed by
 * `state_update` in the same tick. If the `state_update` handler lived on
 * `GamePage`, it would miss that first snapshot because the router is still
 * mid-transition and `LobbyPage` is the mounted component.
 *
 * Pages keep their *navigation* handlers (push on certain events). Handlers
 * stack — both the layout-level and page-level handler fire for an event.
 */
export function useAppEventSync(): void {
  const $q    = useQuasar();
  const lobby = useLobbyStore();
  const game  = useGameStore();

  useServerProtocol({
    [ServerEventType.WELCOME]: (e) => {
      lobby.isHost = e.is_host;
    },
    [ServerEventType.LOBBY_UPDATE]: (e) => {
      lobby.updateFromLobbyUpdate(e.players, e.available_colors);
    },
    [ServerEventType.STATE_UPDATE]: (e) => {
      game.updateFromStateUpdate(e.state);
    },
    [ServerEventType.AVAILABLE_MOVES]: (e) => {
      game.setAvailableMoves(e.moves);
    },
    [ServerEventType.GAME_OVER]: (e) => {
      game.setWinner(e.winner_username);
    },
    [ServerEventType.ERROR]: (e) => {
      $q.notify({ color: 'negative', message: e.message, icon: 'error' });
    },
  });
}
