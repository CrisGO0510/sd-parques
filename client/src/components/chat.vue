<template>
  <div class="chat-panel column" style="height: 300px;">
    <div class="text-subtitle2 q-mb-sm">💬 Chat</div>

    <!-- Mensajes -->
    <div ref="messagesEl"
         class="col overflow-auto q-pa-xs rounded-borders bg-grey-1"
         style="font-size: 13px;">
      <div v-if="messages.length === 0" class="text-grey text-caption text-center q-mt-md">
        No hay mensajes aún
      </div>
      <div v-for="msg in messages" :key="msg.ts" class="q-mb-xs">
        <span :style="{ color: colorForUser(msg.username), fontWeight: 'bold' }">
          {{ msg.username }}:
        </span>
        <span class="q-ml-xs">{{ msg.message }}</span>
      </div>
    </div>

    <!-- Input -->
    <div class="row q-mt-sm q-gutter-xs">
      <q-input
        v-model="draft"
        dense outlined
        placeholder="Escribe un mensaje..."
        class="col"
        maxlength="200"
        @keyup.enter="sendMessage"
      />
      <q-btn dense flat icon="send" color="primary"
             :disable="!draft.trim()" @click="sendMessage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { useGameStore } from 'src/stores/game';
import { useServerProtocol } from 'src/composables/useServerProtocol';
import { ClientCommandType } from 'src/types/protocol';

const game = useGameStore();
const { send } = useServerProtocol({});

const draft = ref('');
const messagesEl = ref<HTMLElement | null>(null);

const messages = game.chatMessages;

const PIECE_COLORS: Record<string, string> = {
  red:    '#e53935',
  blue:   '#1e88e5',
  green:  '#43a047',
  yellow: '#f9a825',
};

function colorForUser(username: string): string {
  const player = game.state?.players.find(p => p.name === username);
  if (player) return PIECE_COLORS[player.color] ?? '#666';
  return '#666';
}
function sendMessage(): void {
  const text = draft.value.trim();
  if (!text) return;
  send({ type: ClientCommandType.CHAT, message: text });
  draft.value = '';
}

watch(messages, async () => {
  await nextTick();
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
  }
}, { deep: true });
</script>