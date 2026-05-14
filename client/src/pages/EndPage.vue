<template>
  <q-page class="flex flex-center">
    <q-card style="min-width: 300px">
      <q-card-section class="text-center">
        <div class="text-h4">¡Fin del juego!</div>
        <div class="text-h6 q-mt-md">
          Ganador: {{ game.winnerUsername ?? 'empate' }}
        </div>
        <div v-if="isCurrentPlayerWinner" class="text-subtitle1 text-positive q-mt-sm">
          ¡Felicidades, ganaste!
        </div>
      </q-card-section>
      <q-card-actions align="center">
        <q-btn color="primary" label="Volver al menú" @click="onBack" />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useConnectionStore } from 'src/stores/connection';
import { useGameStore } from 'src/stores/game';
import { useLobbyStore } from 'src/stores/lobby';
import { useRankingStore } from 'src/stores/ranking';
import { Route } from 'src/router/routes';

const router        = useRouter();
const conn          = useConnectionStore();
const game          = useGameStore();
const lobby         = useLobbyStore();
const rankingStore  = useRankingStore();

const isCurrentPlayerWinner = computed(() => {
  return game.winnerUsername === rankingStore.currentPlayer?.username;
});

onMounted(async () => {
  // Report the win if the current player won
  if (isCurrentPlayerWinner.value && rankingStore.currentPlayer) {
    try {
      await rankingStore.reportWin();
    } catch (error) {
      console.error('Error reporting win:', error);
    }
  }
});

function onBack(): void {
  conn.disconnect();
  game.reset();
  lobby.reset();
  void router.push(Route.CONNECT);
}
</script>
