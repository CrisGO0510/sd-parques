<template>
  <div class="turn-banner" :class="{ 'my-turn': highlight }">
    {{ text }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { GamePhase } from 'src/types/domain';

const props = defineProps<{
  isMyTurn: boolean;
  currentPlayerName: string | null;
  phase: GamePhase | null;
  alreadyRolledInitial: boolean;
}>();

const text = computed<string>(() => {
  if (props.phase === GamePhase.SETUP) {
    return props.alreadyRolledInitial
      ? 'Esperando a los demás jugadores…'
      : 'Lanza tu dado inicial';
  }
  if (props.isMyTurn) return 'Tu turno';
  if (props.currentPlayerName) return `Turno de ${props.currentPlayerName}`;
  return 'Esperando…';
});

// Highlight (green) when it's your turn OR when you can still roll your
// initial die during SETUP.
const highlight = computed<boolean>(() =>
  props.isMyTurn || (props.phase === GamePhase.SETUP && !props.alreadyRolledInitial)
);
</script>

<style scoped>
.turn-banner {
  padding: 16px;
  text-align: center;
  font-size: 20px;
  background: #eee;
}
.turn-banner.my-turn {
  background: #4caf50;
  color: white;
  font-weight: bold;
}
</style>
