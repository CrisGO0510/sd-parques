<template>
  <q-card v-if="recommendation" bordered class="q-mt-md">
    <q-card-section>
      <div class="text-subtitle2">Recomendacion IA</div>
      <p>{{ recommendation.explanation }}</p>
      <q-chip v-if="recommendation.recommendation" color="primary" text-color="white">
        Ficha {{ recommendation.recommendation.piece_index + 1 }}
        (score: {{ recommendation.recommendation.score }})
      </q-chip>
    </q-card-section>
  </q-card>
</template>

<script setup>
defineProps({ recommendation: Object })
</script>
