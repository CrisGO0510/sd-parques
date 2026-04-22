<template>
  <svg :viewBox="`0 0 ${BOARD_SIZE} ${BOARD_SIZE}`" class="board-svg">
    <!-- Background: full parqués board drawn in Inkscape. All geometry
         coordinates are in the SVG's native 1920×1920 coord system. -->
    <image :href="boardImageUrl" :width="BOARD_SIZE" :height="BOARD_SIZE" x="0" y="0" />

    <!-- Debug overlay: one numbered dot per cell, to validate coords. -->
    <g v-if="debug">
      <g v-for="d in debugDots" :key="d.key">
        <circle :cx="d.point.x" :cy="d.point.y" :r="28" fill="white"
                stroke="black" stroke-width="2" opacity="0.85" />
        <text :x="d.point.x" :y="d.point.y + 4"
              text-anchor="middle" font-size="22" fill="black"
              font-family="monospace" font-weight="bold">
          {{ d.label }}
        </text>
      </g>
    </g>

    <!-- Pieces rendered via <PieceToken> slot. -->
    <slot name="pieces" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Color } from 'src/types/domain';
import boardImageUrl from 'src/assets/board.svg';
import {
  BOARD_SIZE,
  CIRCUIT_SIZE,
  circuitCellCenter,
  homeStretchCellCenter,
  jailSlotCenter,
  HOME_STRETCH_SIZE,
  JAIL_SLOTS,
  type Point,
} from 'src/composables/useBoardGeometry';

const props = withDefaults(defineProps<{ debug?: boolean }>(), { debug: false });

interface DebugDot { key: string; point: Point; label: string }

// Builds the full 144-point grid: 96 circuit + 32 home stretches + 16
// jail slots. Labels let you cross-check against the Inkscape source.
const debugDots = computed<DebugDot[]>(() => {
  if (!props.debug) return [];
  const dots: DebugDot[] = [];
  for (let p = 0; p < CIRCUIT_SIZE; p++) {
    dots.push({ key: `c${p}`, point: circuitCellCenter(p), label: String(p) });
  }
  const colors: Color[] = [Color.RED, Color.GREEN, Color.BLUE, Color.YELLOW];
  const colorShort: Record<Color, string> = {
    [Color.RED]: 'R',
    [Color.GREEN]: 'G',
    [Color.BLUE]: 'B',
    [Color.YELLOW]: 'Y',
  };
  for (const color of colors) {
    for (let i = 0; i < HOME_STRETCH_SIZE; i++) {
      dots.push({
        key: `hs-${color}-${i}`,
        point: homeStretchCellCenter(color, i),
        label: `${colorShort[color]}h${i}`,
      });
    }
    for (let s = 0; s < JAIL_SLOTS; s++) {
      dots.push({
        key: `j-${color}-${s}`,
        point: jailSlotCenter(color, s),
        label: `${colorShort[color]}j${s}`,
      });
    }
  }
  return dots;
});
</script>

<style scoped>
.board-svg {
  width: 100%;
  max-width: 720px;
  height: auto;
  display: block;
  margin: 0 auto;
}
</style>
