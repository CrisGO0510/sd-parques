<template>
  <q-list>
    <q-item
      v-for="(p, idx) in players" :key="p.name"
      :class="{ 'bg-primary text-white': idx === currentTurnIndex }"
    >
      <q-item-section avatar>
        <q-avatar :style="avatarStyle(p.color)" text-color="white">
          {{ p.name.charAt(0).toUpperCase() }}
        </q-avatar>
      </q-item-section>
      <q-item-section>
        <q-item-label>{{ p.name }}</q-item-label>
        <q-item-label caption>{{ crownedCount(p) }} / 4 coronadas</q-item-label>
      </q-item-section>
    </q-item>
  </q-list>
</template>

<script setup lang="ts">
import { Color, PieceState } from 'src/types/domain';
import type { PlayerDto } from 'src/types/domain';

defineProps<{
  players: PlayerDto[];
  currentTurnIndex: number;
}>();

const COLOR_HEX: Record<Color, string> = {
  [Color.RED]:    '#e74c3c',
  [Color.BLUE]:   '#3498db',
  [Color.GREEN]:  '#27ae60',
  [Color.YELLOW]: '#f1c40f',
};

function avatarStyle(color: Color): Record<string, string> {
  return { backgroundColor: COLOR_HEX[color] };
}

function crownedCount(p: PlayerDto): number {
  return p.pieces.filter(x => x.state === PieceState.CROWNED).length;
}
</script>
