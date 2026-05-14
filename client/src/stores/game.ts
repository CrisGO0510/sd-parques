import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Color, GamePhase, GameStateDto, MoveDto } from 'src/types/domain';

export interface LastRoll { d1: number; d2: number; isPair: boolean }

export const useGameStore = defineStore('game', () => {
  const state = ref<GameStateDto | null>(null);
  const availableMoves = ref<MoveDto[]>([]);
  const myColor = ref<Color | null>(null);
  const winnerUsername = ref<string | null>(null);
  // Most recent dice roll. Survives across state updates so the player
  // can still see what they rolled even when `pending_dice` has been
  // cleared (e.g., non-pair roll while all pieces are in jail).
  const lastRoll = ref<LastRoll | null>(null);
  const recommendation = ref<{ piece_index: number; action: string; dice_value: number } | null>(null);
  interface ChatMessage { username: string; message: string; ts: number }
  const chatMessages = ref<ChatMessage[]>([]);

  const currentTurnColor = computed<Color | null>(() => {
    const st = state.value;
    if (!st || st.turn_order.length === 0) return null;
    const playerIdx = st.turn_order[st.current_turn_index];
    return playerIdx !== undefined ? (st.players[playerIdx]?.color ?? null) : null;
  });

  const isMyTurn = computed<boolean>(() =>
    myColor.value !== null && currentTurnColor.value === myColor.value
  );

  const phase = computed<GamePhase | null>(() => state.value?.phase ?? null);

  const dice = computed<[number, number] | null>(() => {
    const pd = state.value?.pending_dice;
    if (!pd || pd.length !== 2) return null;
    return [pd[0]!, pd[1]!];
  });

  function updateFromStateUpdate(newState: GameStateDto): void {
    state.value = newState;
  }

  function setAvailableMoves(moves: MoveDto[]): void {
    availableMoves.value = moves;
  }

  function setRecommendation(r: { piece_index: number; action: string; dice_value: number } | null): void {
  recommendation.value = r;
  }
  function addChatMessage(username: string, message: string): void {
    chatMessages.value.push({ username, message, ts: Date.now() });
  }

  function setWinner(u: string | null): void {
    winnerUsername.value = u;
  }

  function setLastRoll(r: LastRoll): void {
    lastRoll.value = r;
  }

  function reset(): void {
    state.value = null;
    availableMoves.value = [];
    myColor.value = null;
    winnerUsername.value = null;
    lastRoll.value = null;
    recommendation.value = null;
  }

  return {
    state,
    availableMoves,
    myColor,
    winnerUsername,
    lastRoll,
    recommendation,
    chatMessages,
    currentTurnColor,
    isMyTurn,
    phase,
    dice,
    updateFromStateUpdate,
    setAvailableMoves,
    setWinner,
    setLastRoll,
    setRecommendation,
    addChatMessage,
    reset,
  };
});
