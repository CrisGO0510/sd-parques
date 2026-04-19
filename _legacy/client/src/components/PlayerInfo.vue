<template>
  <q-list bordered separator>
    <q-item v-for="player in players" :key="player.username"
      :class="{ 'bg-blue-1': player.color === currentTurn }">
      <q-item-section avatar>
        <q-avatar :style="{ background: colorMap[player.color] }" text-color="white">
          {{ player.username[0].toUpperCase() }}
        </q-avatar>
      </q-item-section>
      <q-item-section>
        <q-item-label>{{ player.username }}</q-item-label>
        <q-item-label caption>{{ player.color }}</q-item-label>
      </q-item-section>
      <q-item-section side>
        <q-icon v-if="player.color === currentTurn" name="arrow_forward" color="primary" />
      </q-item-section>
    </q-item>
  </q-list>
</template>

<script setup>
defineProps({ players: Array, currentTurn: String })
const colorMap = { red: '#e74c3c', blue: '#3498db', green: '#27ae60', yellow: '#f1c40f' }
</script>
