<template>
  <q-page class="q-pa-md">
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
            <q-item-label>{{ p.username }}</q-item-label>
            <q-item-label caption>{{ p.color ?? 'sin color' }}</q-item-label>
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

    <div v-if="lobby.isHost">
      <q-btn color="positive" size="lg" :disable="!lobby.canStart" @click="onStart">
        Iniciar partida
      </q-btn>
    </div>
    <div v-else class="text-caption">Esperando al host…</div>
  </q-page>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useLobbyStore } from 'src/stores/lobby';
import { useGameStore } from 'src/stores/game';
import { useServerProtocol } from 'src/composables/useServerProtocol';
import { ClientCommandType, ServerEventType } from 'src/types/protocol';
import { Color } from 'src/types/domain';
import { Route } from 'src/router/routes';

const $q     = useQuasar();
const router = useRouter();
const lobby  = useLobbyStore();
const game   = useGameStore();

const { send } = useServerProtocol({
  [ServerEventType.LOBBY_UPDATE]: (e) => {
    lobby.updateFromLobbyUpdate(e.players, e.available_colors);
  },
  [ServerEventType.GAME_STARTED]: () => {
    game.myColor = lobby.myColor;
    void router.push(Route.GAME);
  },
  [ServerEventType.ERROR]: (e) => {
    $q.notify({ color: 'negative', message: e.message });
  },
});

const COLOR_HEX: Record<Color, string> = {
  [Color.RED]:    '#e74c3c',
  [Color.BLUE]:   '#3498db',
  [Color.GREEN]:  '#27ae60',
  [Color.YELLOW]: '#f1c40f',
};

function avatarStyle(color: Color | null): Record<string, string> {
  return { backgroundColor: color ? COLOR_HEX[color] : '#999' };
}

function colorBtnStyle(color: Color): Record<string, string> {
  return { backgroundColor: COLOR_HEX[color], color: 'white' };
}

function onSelectColor(c: Color): void {
  lobby.myColor = c;
  send({ type: ClientCommandType.SELECT_COLOR, color: c });
}

function onStart(): void {
  send({ type: ClientCommandType.START_GAME });
}
</script>
