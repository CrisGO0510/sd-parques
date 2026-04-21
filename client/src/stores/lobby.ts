import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Color, LobbyPlayerDto } from 'src/types/domain';

export const useLobbyStore = defineStore('lobby', () => {
  const players         = ref<LobbyPlayerDto[]>([]);
  const availableColors = ref<Color[]>([]);
  const isHost          = ref<boolean>(false);
  const myColor         = ref<Color | null>(null);

  const canStart = computed<boolean>(() =>
    players.value.length >= 2 && players.value.every(p => p.color !== null)
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
