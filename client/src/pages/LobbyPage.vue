<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">
      <!-- Sección izquierda: Selección de color y control de partida -->
      <div class="col-12 col-lg-6">
        <div class="text-h5 q-mb-md">Sala de espera</div>

        <q-card class="q-mb-md">
          <q-list>
            <q-item v-for="p in lobby.players" :key="p.username">
              <q-item-section avatar>
                <q-avatar :style="avatarStyle(p.color)" text-color="white">
                  {{ p.username.charAt(0).toUpperCase() }}
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label>
                  {{ p.username }}
                  <q-badge v-if="p.is_bot" color="grey" class="q-ml-sm">BOT</q-badge>
                </q-item-label>
                <q-item-label caption>{{ p.color ?? 'sin color' }}</q-item-label>
              </q-item-section>
              <q-item-section side v-if="lobby.isHost && p.is_bot && p.color">
                <q-btn
                  flat
                  dense
                  round
                  icon="close"
                  size="sm"
                  color="negative"
                  :aria-label="`Quitar ${p.username}`"
                  @click="onRemoveBot(p.color)"
                />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>

        <div class="q-mb-md">
          <div class="text-subtitle1 q-mb-sm">Elige tu color</div>
          <div class="row q-gutter-sm">
            <q-btn
              v-for="c in lobby.availableColors"
              :key="c"
              :label="c"
              :style="colorBtnStyle(c)"
              @click="onSelectColor(c)"
            />
          </div>
        </div>

        <div v-if="lobby.isHost" class="row q-gutter-sm items-center">
          <q-btn color="positive" size="lg" :disable="!lobby.canStart" @click="onStart">
            Iniciar partida
          </q-btn>
          <q-btn
            v-if="canAddBot"
            color="secondary"
            icon="smart_toy"
            label="Agregar bot"
            @click="onAddBot"
          />
        </div>
        <div v-else class="text-caption">Esperando al host…</div>
      </div>

      <!-- Sección derecha: Ranking -->
      <div class="col-12 col-lg-6">
        <q-card>
          <q-card-section>
            <div class="row items-center">
              <div class="col">
                <div class="text-h6">Ranking de Jugadores</div>
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
              :columns="rankingColumns"
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
import { useRouter } from 'vue-router';
import { useLobbyStore } from 'src/stores/lobby';
import { useGameStore } from 'src/stores/game';
import type { PlayerStats } from 'src/stores/ranking';
import { useRankingStore } from 'src/stores/ranking';
import { useServerProtocol } from 'src/composables/useServerProtocol';
import { ClientCommandType, ServerEventType } from 'src/types/protocol';
import { Color } from 'src/types/domain';
import { Route } from 'src/router/routes';

import { computed, onMounted } from 'vue';

const MAX_BOTS = 3;
const MAX_PLAYERS = 4;

const router = useRouter();
const lobby  = useLobbyStore();
const game   = useGameStore();
const rankingStore = useRankingStore();

// LOBBY_UPDATE / ERROR are handled in MainLayout (useAppEventSync). We only
// own GAME_STARTED here for the navigation: pass myColor into the game
// store and push to /game.
const { send } = useServerProtocol({
  [ServerEventType.GAME_STARTED]: () => {
    game.myColor = lobby.myColor;
    void router.push(Route.GAME);
  },
});

const COLOR_HEX: Record<Color, string> = {
  [Color.RED]:    '#e74c3c',
  [Color.BLUE]:   '#3498db',
  [Color.GREEN]:  '#27ae60',
  [Color.YELLOW]: '#f1c40f',
};

const rankingColumns = [
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

function avatarStyle(color: Color | null): Record<string, string> {
  return { backgroundColor: color ? COLOR_HEX[color] : '#999' };
}

function colorBtnStyle(color: Color): Record<string, string> {
  return { backgroundColor: COLOR_HEX[color], color: 'white' };
}

function calculateWinPercentage(player: PlayerStats): number {
  if (!player.games_played || player.games_played === 0) return 0;
  return Math.round((player.games_won / player.games_played) * 100);
}

function onSelectColor(c: Color): void {
  lobby.myColor = c;
  send({ type: ClientCommandType.SELECT_COLOR, color: c });
}

function onStart(): void {
  send({ type: ClientCommandType.START_GAME });
}

const canAddBot = computed<boolean>(() =>
  lobby.isHost
  && lobby.players.length < MAX_PLAYERS
  && lobby.players.filter(p => p.is_bot).length < MAX_BOTS
  && lobby.availableColors.length > 0,
);

function onAddBot(): void {
  lobby.addBot();
}

function onRemoveBot(color: Color): void {
  lobby.removeBot(color);
}

async function loadRanking(): Promise<void> {
  try {
    await rankingStore.fetchRanking();
  } catch (error) {
    console.error('Error loading ranking:', error);
  }
}

// Cargar el ranking cuando se monta el componente
onMounted(async () => {
  await loadRanking();
});
</script>
