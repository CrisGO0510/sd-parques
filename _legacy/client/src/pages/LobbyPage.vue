<template>
  <q-page class="q-pa-md">
    <div class="text-h4 text-center q-mb-lg">Sala de Espera</div>
    <div class="row justify-center q-gutter-md">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Jugadores ({{ lobbyPlayers.length }}/4)</div>
        </q-card-section>
        <q-list separator>
          <q-item v-for="player in lobbyPlayers" :key="player.username">
            <q-item-section avatar>
              <q-avatar :color="player.color || 'grey'" text-color="white">
                {{ player.username[0].toUpperCase() }}
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ player.username }}</q-item-label>
              <q-item-label caption>{{ player.color || 'Sin color' }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section>
          <div class="text-subtitle2 q-mb-sm">Elige tu color:</div>
          <div class="row q-gutter-sm">
            <q-btn v-for="color in availableColors" :key="color"
              :color="color === 'yellow' ? 'amber' : color"
              :label="color" @click="selectColor(color)"
              :outline="myColor !== color" />
          </div>
        </q-card-section>
        <q-card-actions align="center">
          <q-btn v-if="isHost" label="Iniciar Partida" color="positive" size="lg"
            :disable="!canStart" @click="startGame" />
          <div v-else class="text-caption">Esperando a que el host inicie...</div>
        </q-card-actions>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSocket } from 'src/composables/useSocket'
import { useUserStore } from 'src/stores/userStore'
import { useGameStore } from 'src/stores/gameStore'

const router = useRouter()
const userStore = useUserStore()
const gameStore = useGameStore()
const { connect, getSocket } = useSocket()

const lobbyPlayers = ref([])
const availableColors = ref([])
const isHost = ref(false)
const canStart = ref(false)
const myColor = ref('')

onMounted(() => {
  const socket = connect()
  socket.emit('join_lobby', { token: userStore.token })
  socket.on('lobby_update', (data) => {
    lobbyPlayers.value = data.players
    availableColors.value = data.available_colors
    if (data.is_host !== undefined) isHost.value = data.is_host
    canStart.value = lobbyPlayers.value.length >= 2 && lobbyPlayers.value.every(p => p.color)
  })
  socket.on('game_start', (state) => {
    gameStore.updateFromState(state)
    gameStore.setMyColor(myColor.value)
    gameStore.setPlayers(lobbyPlayers.value)
    router.push('/game')
  })
  socket.on('error', (data) => { console.error('Socket error:', data.message) })
})

function selectColor(color) {
  myColor.value = color
  getSocket().emit('select_color', { color })
}

function startGame() {
  getSocket().emit('start_game')
}

onUnmounted(() => {
  const socket = getSocket()
  if (socket) socket.emit('leave_lobby')
})
</script>
