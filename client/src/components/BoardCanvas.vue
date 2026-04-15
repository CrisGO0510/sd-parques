<template>
  <div class="board-container">
    <svg :viewBox="`0 0 ${SIZE} ${SIZE}`" class="board-svg">
      <rect :width="SIZE" :height="SIZE" fill="#f5e6c8" rx="8" />

      <!-- Corner jails -->
      <g v-for="(jail, i) in jails" :key="'jail-'+i">
        <rect :x="jail.x" :y="jail.y" :width="CORNER" :height="CORNER"
          :fill="jail.color" opacity="0.3" rx="4" />
        <text :x="jail.x + CORNER/2" :y="jail.y + 20"
          text-anchor="middle" font-size="10" fill="#333" font-weight="bold">CARCEL</text>
        <!-- Jail pieces -->
        <circle v-for="(piece, pi) in getJailPieces(jail.playerColor)"
          :key="'jp-'+jail.playerColor+'-'+pi"
          :cx="jail.x + 35 + (pi % 2) * 70" :cy="jail.y + 50 + Math.floor(pi / 2) * 50"
          :r="15" :fill="COLOR_MAP[jail.playerColor]" stroke="#333" stroke-width="2"
          :class="{ clickable: isClickable(piece, jail.playerColor) }"
          @click="onPieceClick(piece, jail.playerColor)" />
      </g>

      <!-- Main circuit cells -->
      <g v-for="(cell, idx) in cells" :key="'cell-'+idx">
        <rect :x="cell.x" :y="cell.y" :width="CELL" :height="CELL"
          :fill="getCellFill(idx)" stroke="#999" stroke-width="0.5" rx="2" />
      </g>

      <!-- Home stretch cells -->
      <g v-for="color in activeColors" :key="'hs-'+color">
        <rect v-for="(cell, i) in getHomeStretchCells(color)" :key="'hsc-'+color+'-'+i"
          :x="cell.x" :y="cell.y" :width="CELL" :height="CELL"
          :fill="COLOR_MAP[color]" opacity="0.4" stroke="#999" stroke-width="0.5" rx="2" />
        <!-- Home stretch pieces -->
        <circle v-for="piece in getHomePieces(color)" :key="'hp-'+color+'-'+piece.index"
          :cx="getHomeStretchCells(color)[piece.home_position].x + CELL/2"
          :cy="getHomeStretchCells(color)[piece.home_position].y + CELL/2"
          :r="12" :fill="COLOR_MAP[color]" stroke="#333" stroke-width="2"
          :class="{ clickable: isClickable(piece, color) }"
          @click="onPieceClick(piece, color)" />
      </g>

      <!-- Center circle (META) -->
      <circle :cx="SIZE/2" :cy="SIZE/2" :r="CELL*1.8" fill="#87CEEB" stroke="#666" stroke-width="1.5" />
      <text :x="SIZE/2" :y="SIZE/2" text-anchor="middle" dominant-baseline="middle"
        font-size="14" fill="#333" font-weight="bold">META</text>

      <!-- Board pieces -->
      <g v-for="color in activeColors" :key="'bp-'+color">
        <circle v-for="piece in getBoardPieces(color)" :key="'p-'+color+'-'+piece.index"
          :cx="cells[piece.position]?.x + CELL/2" :cy="cells[piece.position]?.y + CELL/2"
          :r="12" :fill="COLOR_MAP[color]" stroke="#333" stroke-width="2"
          :class="{ clickable: isClickable(piece, color) }"
          @click="onPieceClick(piece, color)" />
      </g>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useGameStore } from 'src/stores/gameStore'

const emit = defineEmits(['piece-click'])
const gameStore = useGameStore()

const SIZE = 520
const CELL = 30
const CORNER = 150

const COLOR_MAP = {
  red: '#e74c3c', blue: '#3498db', green: '#27ae60', yellow: '#f1c40f',
}

const SAFE_POSITIONS = new Set([5, 12, 22, 29, 39, 46, 56, 63])
const EXIT_POSITIONS = { red: 0, blue: 17, green: 34, yellow: 51 }

const jails = [
  { x: 10, y: 10, color: '#e74c3c', playerColor: 'red' },
  { x: SIZE - CORNER - 10, y: 10, color: '#27ae60', playerColor: 'green' },
  { x: 10, y: SIZE - CORNER - 10, color: '#f1c40f', playerColor: 'yellow' },
  { x: SIZE - CORNER - 10, y: SIZE - CORNER - 10, color: '#3498db', playerColor: 'blue' },
]

const board = computed(() => gameStore.board)
const activeColors = computed(() => Object.keys(board.value))

// Build the 68 main circuit cells in a cross pattern
const cells = computed(() => {
  const c = []
  const mid = SIZE / 2
  const arm = CORNER + 15

  // Top arm: cells going down on the left, then up on the right
  for (let i = 0; i < 7; i++) {
    c.push({ x: mid - CELL * 1.5 - CELL, y: arm + i * CELL })
  }
  // Top to right corner
  c.push({ x: mid - CELL / 2, y: arm + 6 * CELL })
  // Right arm: cells going right on top row
  for (let i = 0; i < 7; i++) {
    c.push({ x: mid + CELL / 2 + CELL + i * CELL, y: mid - CELL * 1.5 - CELL })
  }
  // Right to bottom corner
  c.push({ x: SIZE - arm - CELL, y: mid - CELL / 2 })
  for (let i = 0; i < 7; i++) {
    c.push({ x: SIZE - arm - CELL, y: mid + CELL / 2 + CELL + i * CELL })
  }
  // Pad remaining cells around
  while (c.length < 68) {
    const angle = (c.length / 68) * Math.PI * 2 - Math.PI / 2
    const radius = mid - CORNER - 20
    c.push({
      x: mid + Math.cos(angle) * radius - CELL / 2,
      y: mid + Math.sin(angle) * radius - CELL / 2,
    })
  }
  return c.slice(0, 68)
})

function getCellFill(idx) {
  if (Object.values(EXIT_POSITIONS).includes(idx)) return '#ffeb3b'
  if (SAFE_POSITIONS.has(idx)) return '#c8e6c9'
  return '#fff'
}

function getHomeStretchCells(color) {
  const mid = SIZE / 2
  const hsCells = []
  const dirs = {
    red: { x: mid - CELL / 2, y: CORNER + 20, dx: 0, dy: CELL },
    blue: { x: mid - CELL / 2, y: SIZE - CORNER - 20 - CELL, dx: 0, dy: -CELL },
    green: { x: SIZE - CORNER - 20 - CELL, y: mid - CELL / 2, dx: -CELL, dy: 0 },
    yellow: { x: CORNER + 20, y: mid - CELL / 2, dx: CELL, dy: 0 },
  }
  const d = dirs[color]
  if (!d) return hsCells
  for (let i = 0; i < 8; i++) {
    hsCells.push({ x: d.x + d.dx * i, y: d.y + d.dy * i })
  }
  return hsCells
}

function getBoardPieces(color) {
  if (!board.value[color]) return []
  return board.value[color].filter(p => p.state === 'board')
}

function getJailPieces(color) {
  if (!board.value[color]) return []
  return board.value[color].filter(p => p.state === 'jail')
}

function getHomePieces(color) {
  if (!board.value[color]) return []
  return board.value[color].filter(p => p.state === 'home_stretch')
}

function isClickable(piece, color) {
  return gameStore.isMyTurn && color === gameStore.myColor && gameStore.phase === 'moving'
}

function onPieceClick(piece, color) {
  if (isClickable(piece, color)) {
    emit('piece-click', { piece_index: piece.index })
  }
}
</script>

<style scoped>
.board-container {
  display: flex;
  justify-content: center;
  align-items: center;
}
.board-svg {
  width: 100%;
  max-width: 520px;
  height: auto;
}
.clickable {
  cursor: pointer;
  filter: drop-shadow(0 0 4px rgba(255, 255, 0, 0.8));
}
.clickable:hover {
  filter: drop-shadow(0 0 8px rgba(255, 255, 0, 1));
}
</style>
