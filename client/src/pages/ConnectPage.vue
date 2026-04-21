<template>
  <q-page class="q-pa-md flex flex-center">
    <q-card style="min-width: 320px; max-width: 400px; width: 100%">
      <q-card-section>
        <div class="text-h5">Conectar al servidor</div>
      </q-card-section>
      <q-card-section>
        <q-input v-model="host" label="Host" :rules="[v => !!v || 'Requerido']" />
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
import { useLobbyStore } from 'src/stores/lobby';
import { useServerProtocol } from 'src/composables/useServerProtocol';
import { ClientCommandType, ServerEventType } from 'src/types/protocol';
import { Route } from 'src/router/routes';

const STORAGE_HOST     = 'parques.host';
const STORAGE_PORT     = 'parques.port';
const STORAGE_USERNAME = 'parques.username';

const $q       = useQuasar();
const router   = useRouter();
const conn     = useConnectionStore();
const lobby    = useLobbyStore();

const host     = ref<string>(localStorage.getItem(STORAGE_HOST) ?? 'localhost');
const storedPort = Number(localStorage.getItem(STORAGE_PORT));
const port     = ref<number>(Number.isFinite(storedPort) && storedPort > 0 ? storedPort : 5001);
const username = ref<string>(localStorage.getItem(STORAGE_USERNAME) ?? '');
const connecting = ref<boolean>(false);

const { send } = useServerProtocol({
  [ServerEventType.WELCOME]: (e) => {
    lobby.isHost = e.is_host;
    void router.push(Route.LOBBY);
  },
  [ServerEventType.ERROR]: (e) => {
    $q.notify({ color: 'negative', message: e.message, icon: 'error' });
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
    send({ type: ClientCommandType.JOIN, username: username.value });
  } catch {
    connecting.value = false;
    $q.notify({ color: 'negative', message: 'No se pudo conectar', icon: 'error' });
  }
}
</script>
