import { useQuasar } from 'quasar';
import { useServerProtocol } from 'src/composables/useServerProtocol';
import { useGameStore } from 'src/stores/game';
import { useLobbyStore } from 'src/stores/lobby';
import { ServerEventType, ClientCommandType } from 'src/types/protocol';
import { friendlyErrorMessage } from 'src/types/errorMessages';
import { useConnectionStore } from 'src/stores/connection';

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
  const connectionStore = useConnectionStore();

  useServerProtocol({
    [ServerEventType.WELCOME]: (e) => {
      lobby.isHost = e.is_host;
    },
    [ServerEventType.TIME_REQUEST]: () => {
      const clientTime = Date.now();
      connectionStore.send({
        type: ClientCommandType.TIME_RESPONSE,
        client_time: clientTime,
      });
    },
    [ServerEventType.TIME_ADJUST]: (e) => {
      // Guardar el ajuste para usarlo en logs o mostrar en debug
      console.info(`[Berkeley] ajuste de reloj: ${e.adjust_ms}ms`);
    },
    [ServerEventType.LOBBY_UPDATE]: (e) => {
      lobby.updateFromLobbyUpdate(e.players, e.available_colors);
    },
    [ServerEventType.STATE_UPDATE]: (e) => {
      game.updateFromStateUpdate(e.state);
    },
    [ServerEventType.DICE_RESULT]: (e) => {
      game.setLastRoll({ d1: e.d1, d2: e.d2, isPair: e.is_pair });
      const msg = e.is_pair
        ? `¡Par de ${e.d1}! (suma ${e.d1 + e.d2})`
        : `Dados: ${e.d1} y ${e.d2} (suma ${e.d1 + e.d2})`;
      $q.notify({ color: 'info', message: msg, icon: 'casino', timeout: 1800 });
    },
    [ServerEventType.INITIAL_ROLL]: (e) => {
      game.setLastRoll({ d1: e.d1, d2: e.d2, isPair: e.d1 === e.d2 });
      $q.notify({
        color: 'info',
        message: `${e.username} sacó ${e.total} (${e.d1} + ${e.d2})`,
        icon: 'casino',
        timeout: 1800,
      });
    },
    [ServerEventType.AVAILABLE_MOVES]: (e) => {
      game.setAvailableMoves(e.moves);
    },
    [ServerEventType.RECOMMENDATION]: (e) => { 
      game.setRecommendation({ 
        piece_index: e.piece_index, 
        action: e.action, 
        dice_value: e.dice_value 
      }); 
    },
    [ServerEventType.CHAT]: (e) => {
      game.addChatMessage(e.username, e.message);
    },
    [ServerEventType.GAME_OVER]: (e) => {
      game.setWinner(e.winner_username);
    },
    [ServerEventType.ERROR]: (e) => {
      $q.notify({
        color: 'negative',
        message: friendlyErrorMessage(e.code, e.message),
        icon: 'error',
        position: 'bottom',
        timeout: 3000,
      });
    },
  });
}
