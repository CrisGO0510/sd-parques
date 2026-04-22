import { Color } from 'src/types/domain';

export interface Point { x: number; y: number }

// Source coordinate system matches client/src/assets/board.svg (1920×1920).
// All public helpers return coords in this system; the <svg> viewBox must
// be "0 0 1920 1920" so the pieces align with the background image.
export const BOARD_SIZE        = 1920;
export const BOARD_CENTER      = BOARD_SIZE / 2;
export const HOME_STRETCH_SIZE = 8;
export const JAIL_SLOTS        = 4;
export const PIECE_RADIUS      = 35;

// Color arrangement (clockwise visually from RED): RED (bottom-right) →
// GREEN (top-right) → BLUE (top-left) → YELLOW (bottom-left). Movement on
// the circuit is COUNTER-CLOCKWISE (CCW) — RED SALIDA is pos 0, GREEN
// SALIDA is pos 24 (RED + CCW90), BLUE at pos 48 (CCW180), YELLOW at pos
// 72 (CCW270). Must stay in sync with core/board.py EXITS.
const SECTION_FOR_COLOR: Record<Color, number> = {
  [Color.RED]:    0,
  [Color.GREEN]:  1,
  [Color.BLUE]:   2,
  [Color.YELLOW]: 3,
};

// RED's 17 circuit cells in SVG coords. Measured in Inkscape on
// board.svg. Each color's section has 17 cells → 68-cell circuit total.
const RED_CIRCUIT: readonly Point[] = [
  { x: 1210, y: 1570 },  // 0  SALIDA
  { x: 1210, y: 1480 },  // 1
  { x: 1240, y: 1400 },  // 2
  { x: 1265, y: 1325 },  // 3
  { x: 1315, y: 1250 },  // 4
  { x: 1400, y: 1200 },  // 5
  { x: 1480, y: 1190 },  // 6
  { x: 1570, y: 1210 },  // 7  SEGURO (own)
  { x: 1650, y: 1210 },  // 8
  { x: 1730, y: 1210 },  // 9
  { x: 1800, y: 1210 },  // 10
  { x: 1880, y: 1210 },  // 11
  { x: 1890, y:  960 },  // 12  anchor: rotates to each color's LLEGADA entry
  { x: 1890, y:  710 },  // 13  (from YELLOW rotated CCW90)
  { x: 1810, y:  710 },  // 14
  { x: 1730, y:  710 },  // 15
  { x: 1650, y:  710 },  // 16  adjacent to GREEN SALIDA
];

// RED's 8 home-stretch cells in SVG coords. The visible SEGURO cell at
// the foot of the LLEGADA column (y=1890) is shared with the circuit
// entry, so index 0 starts one cell up — the first cell that is
// exclusively part of the home stretch. Index 7 lands on the META
// (center of the board) where the piece is crowned.
const RED_HOME_STRETCH: readonly Point[] = [
  { x: 960, y: 1810 },  // 0  first interior cell
  { x: 960, y: 1730 },  // 1
  { x: 960, y: 1650 },  // 2
  { x: 960, y: 1570 },  // 3
  { x: 960, y: 1490 },  // 4
  { x: 960, y: 1410 },  // 5
  { x: 960, y: 1330 },  // 6  top of LLEGADA column
  { x: 960, y:  960 },  // 7  META (goal)
];

// RED's 4 jail slots — centres of a 2×2 grid inside the jail box
// (1450,1450)-(1800,1800). Pieces are placed inside this square when
// IN_JAIL.
const RED_JAIL_SLOTS: readonly Point[] = [
  { x: 1537.5, y: 1537.5 },  // 0 top-left
  { x: 1712.5, y: 1537.5 },  // 1 top-right
  { x: 1537.5, y: 1712.5 },  // 2 bottom-left
  { x: 1712.5, y: 1712.5 },  // 3 bottom-right
];

// Rotate `p` by (rotIndex × 90°) counter-clockwise around the board
// centre. rotIndex ∈ {0,1,2,3}. For SVG coordinate space (+y goes down),
// visual CCW rotation is (x, y) → (y, 1920 - x); we derive the others
// by composition.
function rotate(p: Point, rotIndex: number): Point {
  const dx = p.x - BOARD_CENTER;
  const dy = p.y - BOARD_CENTER;
  switch (rotIndex & 3) {
    case 0: return { x: BOARD_CENTER + dx, y: BOARD_CENTER + dy };
    case 1: return { x: BOARD_CENTER + dy, y: BOARD_CENTER - dx };
    case 2: return { x: BOARD_CENTER - dx, y: BOARD_CENTER - dy };
    case 3: return { x: BOARD_CENTER - dy, y: BOARD_CENTER + dx };
    default: throw new Error('unreachable');
  }
}

export const CIRCUIT_SIZE         = 68;
export const CELLS_PER_SECTION    = 17;

export function circuitCellCenter(position: number): Point {
  if (position < 0 || position >= CIRCUIT_SIZE) {
    throw new Error(`position out of range: ${position}`);
  }
  const section  = Math.floor(position / CELLS_PER_SECTION);
  const internal = position % CELLS_PER_SECTION;
  return rotate(RED_CIRCUIT[internal]!, section);
}

export function homeStretchCellCenter(color: Color, index: number): Point {
  if (index < 0 || index >= HOME_STRETCH_SIZE) {
    throw new Error(`home_stretch index out of range: ${index}`);
  }
  return rotate(RED_HOME_STRETCH[index]!, SECTION_FOR_COLOR[color]);
}

export function jailSlotCenter(color: Color, slot: number): Point {
  if (slot < 0 || slot >= JAIL_SLOTS) {
    throw new Error(`slot out of range: ${slot}`);
  }
  return rotate(RED_JAIL_SLOTS[slot]!, SECTION_FOR_COLOR[color]);
}

export function goalCenter(): Point {
  return { x: BOARD_CENTER, y: BOARD_CENTER };
}
