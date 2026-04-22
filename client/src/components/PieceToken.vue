<template>
  <g v-if="position" @click="$emit('click')">
    <circle
      :cx="position.x + layout.dx" :cy="position.y + layout.dy" :r="layout.r"
      :fill="fill"
      stroke="#222" stroke-width="3"
      class="piece-circle"
      :class="{ selectable }"
    />
    <g v-if="count > 1">
      <circle
        :cx="position.x + layout.dx + layout.r * 0.75"
        :cy="position.y + layout.dy - layout.r * 0.75"
        :r="layout.r * 0.55"
        fill="#fff" stroke="#222" stroke-width="2"
      />
      <text
        :x="position.x + layout.dx + layout.r * 0.75"
        :y="position.y + layout.dy - layout.r * 0.75"
        text-anchor="middle" dominant-baseline="central"
        :font-size="layout.r * 0.9" fill="#222" font-weight="bold"
      >{{ count }}</text>
    </g>
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { PieceDto } from 'src/types/domain';
import { Color, PieceState } from 'src/types/domain';
import {
  circuitCellCenter,
  homeStretchCellCenter,
  jailSlotCenter,
  PIECE_RADIUS,
} from 'src/composables/useBoardGeometry';

interface Point { x: number; y: number }
interface Layout { dx: number; dy: number; r: number }

const props = withDefaults(defineProps<{
  piece: PieceDto;
  color: Color;
  selectable: boolean;
  count?: number;
  subIndex?: number;
  subTotal?: number;
}>(), { count: 1, subIndex: 0, subTotal: 1 });

defineEmits<{ (e: 'click'): void }>();

const COLOR_HEX: Record<Color, string> = {
  [Color.RED]:    '#e74c3c',
  [Color.BLUE]:   '#3498db',
  [Color.GREEN]:  '#27ae60',
  [Color.YELLOW]: '#f1c40f',
};

const fill = computed<string>(() => COLOR_HEX[props.color]);

const position = computed<Point | null>(() => {
  switch (props.piece.state) {
    case PieceState.IN_JAIL:
      return jailSlotCenter(props.color, props.piece.index);
    case PieceState.ON_BOARD:
      if (props.piece.circuit_position === null) return null;
      return circuitCellCenter(props.piece.circuit_position);
    case PieceState.IN_HOME_STRETCH:
      if (props.piece.home_stretch_position === null) return null;
      return homeStretchCellCenter(props.color, props.piece.home_stretch_position);
    case PieceState.CROWNED:
      return null;  // not rendered on the board
    default:
      return null;
  }
});

// When several colors share a circuit cell we shrink each piece and
// place it at a sub-slot so they all stay visible side by side.
const layout = computed<Layout>(() => {
  const total = props.subTotal;
  if (total <= 1) return { dx: 0, dy: 0, r: PIECE_RADIUS };
  const r = PIECE_RADIUS * 0.55;
  const off = PIECE_RADIUS * 0.6;
  if (total === 2) {
    return { dx: props.subIndex === 0 ? -off : off, dy: 0, r };
  }
  if (total === 3) {
    const slots: Array<[number, number]> = [[-off, -off * 0.55], [off, -off * 0.55], [0, off * 0.85]];
    const [dx, dy] = slots[props.subIndex] ?? [0, 0];
    return { dx, dy, r };
  }
  // 4 or more → 2×2 grid
  const slots: Array<[number, number]> = [[-off, -off], [off, -off], [-off, off], [off, off]];
  const [dx, dy] = slots[Math.min(props.subIndex, 3)] ?? [0, 0];
  return { dx, dy, r };
});
</script>
