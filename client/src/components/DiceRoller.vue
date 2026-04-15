<template>
  <div class="dice-container row q-gutter-md justify-center items-center">
    <div class="dice" :class="{ rolling }">{{ dice[0] || '?' }}</div>
    <div class="dice" :class="{ rolling }">{{ dice[1] || '?' }}</div>
    <q-btn v-if="canRoll" label="Lanzar Dados" color="primary" @click="$emit('roll')" :loading="rolling" />
    <q-chip v-if="isPair" color="amber" text-color="black">PARES!</q-chip>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  dice: { type: Array, default: () => [0, 0] },
  canRoll: Boolean,
  rolling: Boolean,
})
defineEmits(['roll'])
const isPair = computed(() => props.dice[0] > 0 && props.dice[0] === props.dice[1])
</script>

<style scoped>
.dice {
  width: 60px; height: 60px;
  background: white; border: 2px solid #333; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 28px; font-weight: bold;
}
.rolling { animation: shake 0.3s ease-in-out 3; }
@keyframes shake {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-10deg); }
  75% { transform: rotate(10deg); }
}
</style>
