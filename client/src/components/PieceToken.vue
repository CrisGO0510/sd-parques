<template>
  <circle
    v-if="position"
    :cx="position.x" :cy="position.y" :r="PIECE_RADIUS"
    :fill="fill"
    stroke="#222" stroke-width="3"
    class="piece-circle"
    :class="{ selectable }"
    @click="$emit('click')"
  />
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

const props = defineProps<{
  piece: PieceDto;
  color: Color;
  selectable: boolean;
}>();

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
</script>
