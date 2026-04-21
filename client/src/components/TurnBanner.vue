<template>
  <div class="turn-banner" :class="{ 'my-turn': isMyTurn }">
    {{ text }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  isMyTurn: boolean;
  currentPlayerName: string | null;
}>();

const text = computed<string>(() => {
  if (props.isMyTurn) return 'Tu turno';
  if (props.currentPlayerName) return `Turno de ${props.currentPlayerName}`;
  return 'Esperando…';
});
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
