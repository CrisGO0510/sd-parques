<template>
  <q-page class="q-pa-md">
    <div class="row q-gutter-md">
      <div class="col-3">
        <PlayerInfo :players="gameStore.players" :current-turn="gameStore.currentTurn" />
        <RecommendationPanel :recommendation="gameStore.recommendation" class="q-mt-md" />
        <q-btn v-if="gameStore.isMyTurn && gameStore.phase === 'moving'"
          label="Pedir Recomendacion" color="secondary" class="full-width q-mt-md"
          @click="requestRecommendation" />
      </div>
      <div class="col">
        <BoardCanvas @piece-click="onPieceClick" />
      </div>
      <div class="col-3">
        <DiceRoller :dice="gameStore.dice"
          :can-roll="gameStore.isMyTurn && gameStore.phase === 'rolling'"
          @roll="rollDice" />
        <q-btn v-if="gameStore.isMyTurn && gameStore.phase === 'moving'"
          label="Pasar Turno" color="grey" class="full-width q-mt-md" @click="passTurn" />
      </div>
    </div>
    <q-dialog :model-value="!!gameStore.winner" persistent>
      <q-card>
        <q-card-section class="text-center">
          <div class="text-h4">Fin del Juego!</div>
          <div class="text-h5 q-mt-md">Ganador: {{ gameStore.winner }}</div>
        </q-card-section>
        <q-card-actions align="center">
          <q-btn label="Volver al Lobby" color="primary" @click="backToLobby" />
          <q-btn label="Ver Estadisticas" color="secondary" @click="$router.push('/stats')" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from 'src/stores/gameStore'
import { useGame } from 'src/composables/useGame'
import BoardCanvas from 'src/components/BoardCanvas.vue'
import DiceRoller from 'src/components/DiceRoller.vue'
import PlayerInfo from 'src/components/PlayerInfo.vue'
import RecommendationPanel from 'src/components/RecommendationPanel.vue'

const router = useRouter()
const gameStore = useGameStore()
const { rollDice, movePiece, passTurn, requestRecommendation, setupListeners } = useGame()

onMounted(() => { setupListeners() })

function onPieceClick({ piece_index }) { movePiece(piece_index) }
function backToLobby() { gameStore.reset(); router.push('/lobby') }
</script>
