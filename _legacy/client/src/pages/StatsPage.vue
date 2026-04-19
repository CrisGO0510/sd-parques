<template>
  <q-page class="q-pa-md">
    <div class="text-h4 text-center q-mb-lg">Estadisticas</div>
    <div class="row q-gutter-md justify-center">
      <q-card style="min-width: 350px">
        <q-card-section>
          <div class="text-h6">Mis Estadisticas</div>
        </q-card-section>
        <q-card-section v-if="myStats">
          <div class="row q-gutter-md">
            <q-chip color="primary" text-color="white">Partidas: {{ myStats.total_games }}</q-chip>
            <q-chip color="positive" text-color="white">Victorias: {{ myStats.wins }}</q-chip>
            <q-chip color="amber" text-color="black">Probabilidad: {{ (myStats.win_probability * 100).toFixed(1) }}%</q-chip>
          </div>
          <div class="text-subtitle2 q-mt-md">Ultimas partidas</div>
          <q-list separator>
            <q-item v-for="game in myStats.recent_games" :key="game.game_id">
              <q-item-section>
                <q-item-label>Partida #{{ game.game_id }}</q-item-label>
                <q-item-label caption>{{ game.date }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge :color="game.won ? 'positive' : 'negative'">
                  {{ game.won ? 'Victoria' : 'Derrota' }}
                </q-badge>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>
      <q-card style="min-width: 350px">
        <q-card-section>
          <div class="text-h6">Ranking Global</div>
        </q-card-section>
        <q-card-section>
          <q-list separator>
            <q-item v-for="(player, i) in ranking" :key="player.username">
              <q-item-section avatar>
                <q-avatar color="primary" text-color="white">{{ i + 1 }}</q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ player.username }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge color="amber" text-color="black">{{ player.wins }} victorias</q-badge>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>
      <q-card style="min-width: 350px">
        <q-card-section>
          <div class="text-h6">Buscar Jugador</div>
          <q-input v-model="searchUsername" label="Nombre de usuario" outlined
            @keyup.enter="searchPlayer" class="q-mt-sm">
            <template v-slot:append>
              <q-btn icon="search" flat @click="searchPlayer" />
            </template>
          </q-input>
        </q-card-section>
        <q-card-section v-if="searchResult">
          <div>Partidas: {{ searchResult.total_games }}</div>
          <div>Victorias: {{ searchResult.wins }}</div>
          <div>Probabilidad de ganar: {{ (searchResult.win_probability * 100).toFixed(1) }}%</div>
        </q-card-section>
      </q-card>
    </div>
    <div class="text-center q-mt-lg">
      <q-btn label="Volver al Lobby" color="primary" @click="$router.push('/lobby')" />
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useUserStore } from 'src/stores/userStore'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'
const userStore = useUserStore()

const myStats = ref(null)
const ranking = ref([])
const searchUsername = ref('')
const searchResult = ref(null)

onMounted(async () => {
  const [statsRes, rankingRes] = await Promise.all([
    axios.get(`${API_URL}/stats`, { headers: { Authorization: `Bearer ${userStore.token}` } }),
    axios.get(`${API_URL}/ranking`),
  ])
  myStats.value = statsRes.data
  ranking.value = rankingRes.data
})

async function searchPlayer() {
  if (!searchUsername.value) return
  try {
    const { data } = await axios.get(`${API_URL}/stats/${searchUsername.value}`)
    searchResult.value = data
  } catch { searchResult.value = null }
}
</script>
