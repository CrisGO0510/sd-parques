<template>
  <div class="row items-center q-gutter-md">
    <div class="die">{{ d1 ?? '·' }}</div>
    <div class="die">{{ d2 ?? '·' }}</div>
    <q-btn v-if="canRoll" color="primary" size="lg" label="Lanzar" @click="$emit('roll')" />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  d1: number | null;
  d2: number | null;
  canRoll: boolean;
}>();
defineEmits<{ (e: 'roll'): void }>();
</script>

<style scoped>
.die {
  width: 64px; height: 64px;
  border: 2px solid #333; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 32px; font-weight: bold;
  background: white;
}
</style>
