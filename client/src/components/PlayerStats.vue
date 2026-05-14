<template>
  <q-card flat>
    <q-card-section>
      <div class="text-h6">Mi Perfil</div>
    </q-card-section>
    <q-separator />
    <q-card-section v-if="rankingStore.currentPlayerStats">
      <div class="row q-col-gutter-md">
        <div class="col-12 col-sm-6">
          <div class="text-subtitle2 text-grey-7">Jugador</div>
          <div class="text-h6">{{ rankingStore.currentPlayerStats.username }}</div>
        </div>
        <div class="col-12 col-sm-6">
          <div class="text-subtitle2 text-grey-7">Partidas Jugadas</div>
          <div class="text-h6">{{ rankingStore.currentPlayerStats.games_played }}</div>
        </div>
        <div class="col-12 col-sm-6">
          <div class="text-subtitle2 text-grey-7">Victorias</div>
          <div class="text-h6 text-positive">{{ rankingStore.currentPlayerStats.games_won }}</div>
        </div>
        <div class="col-12 col-sm-6">
          <div class="text-subtitle2 text-grey-7">Porcentaje de Victoria</div>
          <div class="text-h6">{{ rankingStore.currentPlayerStats.win_percentage }}%</div>
        </div>
      </div>
    </q-card-section>
    <q-card-section v-else>
      <div class="text-center text-grey-6">
        <p>Cargando datos del jugador...</p>
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { useRankingStore } from 'src/stores/ranking';

const rankingStore = useRankingStore();
</script>
