<template>
  <q-page class="q-pa-md flex flex-center">
    <q-card style="min-width: 320px; max-width: 400px; width: 100%">
      <q-card-section>
        <div class="text-h5">Conectar al servidor</div>
      </q-card-section>
      <q-card-section>
        <q-input v-model="host" label="Servidor" :rules="[v => !!v || 'Requerido']" />
        <q-input v-model.number="port" label="Puerto" type="number"
                 :rules="[(v: number) => (v >= 1 && v <= 65535) || 'Puerto inválido']" />
        <q-input v-model="username" label="Nombre de usuario"
                 :rules="[(v: string) => (v.length >= 3 && v.length <= 20) || '3-20 caracteres']" />
      </q-card-section>
      <q-card-actions align="center">
        <q-btn color="primary" label="Conectar" :loading="connecting" @click="onConnect" />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useConnectionStore } from 'src/stores/connection';
import { useRankingStore } from 'src/stores/ranking';
import { useServerProtocol } from 'src/composables/useServerProtocol';
import { ClientCommandType, ServerEventType } from 'src/types/protocol';
import { Route } from 'src/router/routes';

const STORAGE_HOST     = 'parques.host';
const STORAGE_PORT     = 'parques.port';
const STORAGE_USERNAME = 'parques.username';

function defaultSocketSettings(): { host: string; port: number } | null {
  const configuredUrl = import.meta.env.VITE_WS_URL?.trim();
  if (!configuredUrl) {
    return null;
  }

  try {
    const url = new URL(configuredUrl);
    const port = url.port
      ? Number(url.port)
      : (url.protocol === 'wss:' ? 443 : 80);
    if (!Number.isFinite(port) || port <= 0) {
      return null;
    }
    return { host: url.hostname, port };
  } catch {
    return null;
  }
}

const $q           = useQuasar();
const router       = useRouter();
const conn         = useConnectionStore();
const rankingStore = useRankingStore();

const defaultSocket = defaultSocketSettings();
const host     = ref<string>(localStorage.getItem(STORAGE_HOST) ?? defaultSocket?.host ?? 'localhost');
const storedPort = Number(localStorage.getItem(STORAGE_PORT));
const port     = ref<number>(Number.isFinite(storedPort) && storedPort > 0 ? storedPort : (defaultSocket?.port ?? 5001));
const username = ref<string>(localStorage.getItem(STORAGE_USERNAME) ?? '');
const connecting = ref<boolean>(false);

// MainLayout's useAppEventSync stores lobby.isHost from WELCOME; we only
// need this handler to navigate after that state is in place. The ERROR
// handler clears `connecting` so the user can retry — without it a server
// rejection (e.g. DUPLICATE_PLAYER) would leave the button spinning forever.
const { send } = useServerProtocol({
  [ServerEventType.WELCOME]: () => {
    void router.push(Route.LOBBY);
  },
  [ServerEventType.ERROR]: () => {
    connecting.value = false;
  },
});

async function onConnect(): Promise<void> {
  connecting.value = true;
  try {
    await conn.connect(host.value, port.value, username.value);
    localStorage.setItem(STORAGE_HOST,     host.value);
    localStorage.setItem(STORAGE_PORT,     String(port.value));
    localStorage.setItem(STORAGE_USERNAME, username.value);
    
    // First verify/register the player
    try {
      await rankingStore.verifyPlayer(username.value);
    } catch (error) {
      console.error('Error verifying player:', error);
      // Continue anyway - the game can still work
    }
    
    // Then join the game
    send({ type: ClientCommandType.JOIN, username: username.value });
  } catch {
    connecting.value = false;
    $q.notify({ color: 'negative', message: 'No se pudo conectar', icon: 'error' });
  }
}
</script>
