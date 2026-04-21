import { Color } from 'src/types/domain';

export interface Point { x: number; y: number }

// Layout constants — viewBox 600×600.
export const BOARD_SIZE        = 600;
export const CELL_SIZE         = 30;
export const JAIL_SIZE         = 150;
export const HOME_STRETCH_SIZE = 8;
export const GOAL_RADIUS       = 50;
export const GOAL_CENTER: Point = { x: BOARD_SIZE / 2, y: BOARD_SIZE / 2 };

// Arm index → associated color. Arm 0 = N, then clockwise (E, S, W).
const ARMS: Color[] = [Color.RED, Color.BLUE, Color.GREEN, Color.YELLOW];

export function circuitCellCenter(position: number): Point {
  if (position < 0 || position >= 96) {
    throw new Error(`position out of range: ${position}`);
  }
  const arm       = Math.floor(position / 24);  // 0..3
  const cellInArm = position % 24;              // 0..23
  return armCellCenter(arm, cellInArm);
}

function armCellCenter(arm: number, cellInArm: number): Point {
  const cx = BOARD_SIZE / 2;
  const cy = BOARD_SIZE / 2;

  // Raw L-shape coordinates relative to arm 0 (top).
  // Outer lane (cells 0..7): down the left side toward the jail.
  // Bottom row (cells 8..15): across the bottom of the arm.
  // Inner lane (cells 16..23): up the right side back toward center.
  let rx: number;
  let ry: number;
  if (cellInArm < 8) {
    rx = -CELL_SIZE * 1.5;
    ry = -(BOARD_SIZE / 2) + JAIL_SIZE + 10 + CELL_SIZE * (cellInArm + 0.5);
  } else if (cellInArm < 16) {
    rx = -CELL_SIZE * 1.5 + CELL_SIZE * ((cellInArm - 8) + 0.5);
    ry = -(BOARD_SIZE / 2) + JAIL_SIZE + 10 + CELL_SIZE * 8;
  } else {
    rx = CELL_SIZE * 1.5;
    ry = -(BOARD_SIZE / 2) + JAIL_SIZE + 10 + CELL_SIZE * ((23 - cellInArm) + 0.5);
  }

  // Rotate by 90° × arm around the center.
  const theta = (Math.PI / 2) * arm;
  const x = cx + rx * Math.cos(theta) - ry * Math.sin(theta);
  const y = cy + rx * Math.sin(theta) + ry * Math.cos(theta);
  return { x, y };
}

export function homeStretchCellCenter(color: Color, index: number): Point {
  if (index < 0 || index >= HOME_STRETCH_SIZE) {
    throw new Error(`home_stretch index out of range: ${index}`);
  }
  const arm = ARMS.indexOf(color);
  if (arm < 0) throw new Error(`unknown color: ${color}`);

  const cx = BOARD_SIZE / 2;
  const cy = BOARD_SIZE / 2;
  // index 0 is just after the circuit entry; index 7 is adjacent to the goal.
  const distanceFromCenter =
    (HOME_STRETCH_SIZE - 1 - index) * CELL_SIZE + GOAL_RADIUS + CELL_SIZE / 2;
  const theta = (Math.PI / 2) * arm;
  const rx = 0;
  const ry = -distanceFromCenter;
  const x = cx + rx * Math.cos(theta) - ry * Math.sin(theta);
  const y = cy + rx * Math.sin(theta) + ry * Math.cos(theta);
  return { x, y };
}

export function jailSlotCenter(color: Color, slot: number): Point {
  if (slot < 0 || slot >= 4) throw new Error(`slot out of range: ${slot}`);
  const arm = ARMS.indexOf(color);
  if (arm < 0) throw new Error(`unknown color: ${color}`);

  // Jail corners: N=top-left, E=top-right, S=bottom-right, W=bottom-left.
  const corners: Point[] = [
    { x: 10,                          y: 10                          },
    { x: BOARD_SIZE - JAIL_SIZE - 10, y: 10                          },
    { x: BOARD_SIZE - JAIL_SIZE - 10, y: BOARD_SIZE - JAIL_SIZE - 10 },
    { x: 10,                          y: BOARD_SIZE - JAIL_SIZE - 10 },
  ];
  const corner = corners[arm]!;
  // 2×2 grid of slots inside the jail.
  const slotX = slot % 2;
  const slotY = Math.floor(slot / 2);
  const inset = JAIL_SIZE / 4;
  return {
    x: corner.x + inset + slotX * (JAIL_SIZE / 2),
    y: corner.y + inset + slotY * (JAIL_SIZE / 2),
  };
}

export function goalCenter(): Point {
  return GOAL_CENTER;
}
