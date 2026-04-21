<template>
  <svg :viewBox="`0 0 ${BOARD_SIZE} ${BOARD_SIZE}`" class="board-svg">
    <!-- Fondo -->
    <rect :width="BOARD_SIZE" :height="BOARD_SIZE" fill="#f5e6c8" rx="8" />

    <!-- Cárceles -->
    <g v-for="(color, i) in JAIL_COLORS" :key="'jail-'+i">
      <rect
        :x="jailCorner(i).x" :y="jailCorner(i).y"
        :width="JAIL_SIZE" :height="JAIL_SIZE"
        :fill="COLOR_HEX[color]" fill-opacity="0.3" stroke="#666" rx="4"
      />
      <text
        :x="jailCorner(i).x + JAIL_SIZE / 2"
        :y="jailCorner(i).y + 20"
        text-anchor="middle" font-size="12" fill="#333"
      >CÁRCEL</text>
    </g>

    <!-- Circuit cells -->
    <rect
      v-for="pos in CIRCUIT_POSITIONS" :key="'cell-'+pos"
      :x="circuitCellCenter(pos).x - CELL_SIZE / 2"
      :y="circuitCellCenter(pos).y - CELL_SIZE / 2"
      :width="CELL_SIZE" :height="CELL_SIZE"
      :fill="cellFill(pos)" stroke="#999" stroke-width="0.5" rx="2"
    />

    <!-- Home stretches -->
    <g v-for="color in HOME_STRETCH_COLORS" :key="'hs-'+color">
      <rect
        v-for="i in HOME_STRETCH_INDICES" :key="'hs-'+color+'-'+i"
        :x="homeStretchCellCenter(color, i).x - CELL_SIZE / 2"
        :y="homeStretchCellCenter(color, i).y - CELL_SIZE / 2"
        :width="CELL_SIZE" :height="CELL_SIZE"
        :fill="COLOR_HEX[color]" fill-opacity="0.4"
        stroke="#999" stroke-width="0.5" rx="2"
      />
    </g>

    <!-- Goal -->
    <circle
      :cx="BOARD_SIZE / 2" :cy="BOARD_SIZE / 2" :r="GOAL_RADIUS"
      fill="#87CEEB" stroke="#666" stroke-width="1.5"
    />
    <text
      :x="BOARD_SIZE / 2" :y="BOARD_SIZE / 2"
      text-anchor="middle" dominant-baseline="middle"
      font-size="14" fill="#333" font-weight="bold"
    >META</text>

    <!-- Pieces rendered via <PieceToken> (S19 slot) -->
    <slot name="pieces" />
  </svg>
</template>

<script setup lang="ts">
import { Color } from 'src/types/domain';
import {
  BOARD_SIZE,
  CELL_SIZE,
  JAIL_SIZE,
  GOAL_RADIUS,
  circuitCellCenter,
  homeStretchCellCenter,
} from 'src/composables/useBoardGeometry';

interface Point { x: number; y: number }

const COLOR_HEX: Record<Color, string> = {
  [Color.RED]:    '#e74c3c',
  [Color.BLUE]:   '#3498db',
  [Color.GREEN]:  '#27ae60',
  [Color.YELLOW]: '#f1c40f',
};

// Arm 0 = N/RED, 1 = E/BLUE, 2 = S/GREEN, 3 = W/YELLOW.
const JAIL_COLORS:          readonly Color[]  = [Color.RED, Color.BLUE, Color.GREEN, Color.YELLOW];
const HOME_STRETCH_COLORS:  readonly Color[]  = [Color.RED, Color.BLUE, Color.GREEN, Color.YELLOW];
const CIRCUIT_POSITIONS:    readonly number[] = Array.from({ length: 96 }, (_, i) => i);
const HOME_STRETCH_INDICES: readonly number[] = Array.from({ length: 8 }, (_, i) => i);

// Constants for exits and safes — MUST STAY IN SYNC with core/board.py.
// If the Python motor ever changes EXITS or SAFES, update these two sets.
const EXITS_POSITIONS = new Set<number>([0, 24, 48, 72]);
const SAFE_POSITIONS  = new Set<number>([0, 6, 18, 24, 30, 42, 48, 54, 66, 72, 78, 90]);

function cellFill(pos: number): string {
  if (EXITS_POSITIONS.has(pos)) return '#ffeb3b';
  if (SAFE_POSITIONS.has(pos))  return '#c8e6c9';
  return '#fff';
}

function jailCorner(arm: number): Point {
  const corners: Point[] = [
    { x: 10,                          y: 10                          },
    { x: BOARD_SIZE - JAIL_SIZE - 10, y: 10                          },
    { x: BOARD_SIZE - JAIL_SIZE - 10, y: BOARD_SIZE - JAIL_SIZE - 10 },
    { x: 10,                          y: BOARD_SIZE - JAIL_SIZE - 10 },
  ];
  return corners[arm]!;
}
</script>

<style scoped>
.board-svg {
  width: 100%;
  max-width: 600px;
  height: auto;
  display: block;
  margin: 0 auto;
}
</style>
