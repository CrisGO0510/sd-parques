<template>
  <q-page class="flex flex-center">
    <q-card style="min-width: 300px">
      <q-card-section class="text-center">
        <div class="text-h4">¡Fin del juego!</div>
        <div class="text-h6 q-mt-md">
          Ganador: {{ game.winnerUsername ?? 'empate' }}
        </div>
      </q-card-section>
      <q-card-actions align="center">
        <q-btn color="primary" label="Volver al menú" @click="onBack" />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useConnectionStore } from 'src/stores/connection';
import { useGameStore } from 'src/stores/game';
import { useLobbyStore } from 'src/stores/lobby';
import { Route } from 'src/router/routes';

const router = useRouter();
const conn   = useConnectionStore();
const game   = useGameStore();
const lobby  = useLobbyStore();

function onBack(): void {
  conn.disconnect();
  game.reset();
  lobby.reset();
  void router.push(Route.CONNECT);
}
</script>
