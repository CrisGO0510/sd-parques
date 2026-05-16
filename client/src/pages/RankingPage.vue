<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">
      <div class="col-12 col-lg-4">
        <PlayerStats />
      </div>
      <div class="col-12 col-lg-8">
        <q-card>
          <q-card-section>
            <div class="row items-center">
              <div class="col">
                <div class="text-h6">Ranking Global</div>
              </div>
              <div class="col-auto">
                <q-btn
                  flat
                  dense
                  round
                  icon="refresh"
                  :loading="rankingStore.isLoading"
                  @click="loadRanking"
                  title="Actualizar ranking"
                />
              </div>
            </div>
          </q-card-section>
          <q-separator />
          <q-card-section>
            <q-table
              v-if="rankingStore.ranking.length > 0"
              :rows="rankingStore.ranking"
              :columns="columns"
              row-key="id"
              flat
              bordered
              dense
            >
              <template #body-cell-rank="props">
                <q-td :props="props">
                  <div class="text-weight-bold">
                    {{ props.rowIndex + 1 }}
                  </div>
                </q-td>
              </template>
              <template #body-cell-win_percentage="props">
                <q-td :props="props">
                  <div class="text-weight-bold text-positive">
                    {{ calculateWinPercentage(props.row) }}%
                  </div>
                </q-td>
              </template>
            </q-table>
            <div v-else class="text-center text-grey-6 q-py-md">
              <p v-if="rankingStore.isLoading">Cargando ranking...</p>
              <p v-else>No hay jugadores en el ranking</p>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">

import { onMounted } from 'vue';
import type { PlayerStats as PlayerStatsType } from 'src/stores/ranking';
import { useRankingStore } from 'src/stores/ranking';
import PlayerStats from 'src/components/PlayerStats.vue';

const rankingStore = useRankingStore();

const columns = [
  {
    name: 'rank',
    label: '#',
    field: 'rank',
    align: 'center' as const,
    style: 'width: 50px',
  },
  {
    name: 'username',
    label: 'Jugador',
    field: 'username',
    align: 'left' as const,
  },
  {
    name: 'games_played',
    label: 'Partidas',
    field: 'games_played',
    align: 'center' as const,
  },
  {
    name: 'games_won',
    label: 'Victorias',
    field: 'games_won',
    align: 'center' as const,
  },
  {
    name: 'win_percentage',
    label: '% Victoria',
    field: 'win_percentage',
    align: 'center' as const,
  },
];

function calculateWinPercentage(player: PlayerStatsType): number {
  if (player.games_played === 0) return 0;
  return Math.round((player.games_won / player.games_played) * 100);
}

async function loadRanking(): Promise<void> {
  try {
    await rankingStore.fetchRanking();
  } catch (error) {
    console.error('Error loading ranking:', error);
  }
}

onMounted(() => {
  void loadRanking();
});
</script>
