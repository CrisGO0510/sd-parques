import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Color, LobbyPlayerDto } from 'src/types/domain';

export const useLobbyStore = defineStore('lobby', () => {
  const players         = ref<LobbyPlayerDto[]>([]);
  const availableColors = ref<Color[]>([]);
  const isHost          = ref<boolean>(false);
  const myColor         = ref<Color | null>(null);

  // Puede iniciar si hay al menos 1 humano y todos los jugadores (humanos y
  // bots) tienen color. Los 2 bots fijos ya vienen con color.
  const canStart = computed<boolean>(() =>
    players.value.some(p => !p.is_bot) &&
    players.value.every(p => p.color !== null),
  );

  function updateFromLobbyUpdate(
    newPlayers: LobbyPlayerDto[],
    newAvailable: Color[],
  ): void {
    players.value = newPlayers;
    availableColors.value = newAvailable;
  }

  function reset(): void {
    players.value = [];
    availableColors.value = [];
    isHost.value = false;
    myColor.value = null;
  }

  return { players, availableColors, isHost, myColor, canStart,
           updateFromLobbyUpdate, reset };
});
