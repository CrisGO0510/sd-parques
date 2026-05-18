<template>
  <q-list>
    <q-item
      v-for="(p, idx) in players" :key="p.name"
      :class="{
        'bg-primary text-white': idx === currentTurnIndex && !isDisconnected(p),
        'text-grey-6': isDisconnected(p),
      }"
    >
      <q-item-section avatar>
        <q-avatar :style="avatarStyle(p.color, isDisconnected(p))" text-color="white">
          {{ p.name.charAt(0).toUpperCase() }}
        </q-avatar>
      </q-item-section>
      <q-item-section>
        <q-item-label>
          {{ p.name }}
          <q-badge v-if="p.is_bot" color="grey" class="q-ml-sm">BOT</q-badge>
          <q-badge v-if="isDisconnected(p)" color="grey" class="q-ml-sm">
            desconectado
          </q-badge>
        </q-item-label>
        <q-item-label caption>{{ crownedCount(p) }} / 4 coronadas</q-item-label>
      </q-item-section>
    </q-item>
  </q-list>
</template>

<script setup lang="ts">
import { Color, PieceState } from 'src/types/domain';
import type { PlayerDto } from 'src/types/domain';

const props = defineProps<{
  players: PlayerDto[];
  currentTurnIndex: number;
  disconnectedColors: Color[];
}>();

const COLOR_HEX: Record<Color, string> = {
  [Color.RED]:    '#e74c3c',
  [Color.BLUE]:   '#3498db',
  [Color.GREEN]:  '#27ae60',
  [Color.YELLOW]: '#f1c40f',
};

function avatarStyle(color: Color, disconnected: boolean): Record<string, string> {
  return {
    backgroundColor: COLOR_HEX[color],
    opacity: disconnected ? '0.35' : '1',
  };
}

function crownedCount(p: PlayerDto): number {
  return p.pieces.filter(x => x.state === PieceState.CROWNED).length;
}

function isDisconnected(p: PlayerDto): boolean {
  return props.disconnectedColors.includes(p.color);
}
</script>
