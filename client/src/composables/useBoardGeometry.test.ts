import { describe, expect, it } from 'vitest';
import { Color } from 'src/types/domain';
import {
  BOARD_SIZE,
  BOARD_CENTER,
  CIRCUIT_SIZE,
  circuitCellCenter,
  goalCenter,
  homeStretchCellCenter,
  jailSlotCenter,
} from './useBoardGeometry';

describe('useBoardGeometry', () => {
  it('goal center is at the board centre', () => {
    expect(goalCenter()).toEqual({ x: BOARD_CENTER, y: BOARD_CENTER });
  });

  it('circuit cells are all within the viewBox', () => {
    for (let p = 0; p < CIRCUIT_SIZE; p++) {
      const { x, y } = circuitCellCenter(p);
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThanOrEqual(BOARD_SIZE);
      expect(y).toBeGreaterThanOrEqual(0);
      expect(y).toBeLessThanOrEqual(BOARD_SIZE);
    }
  });

  it('circuitCellCenter throws for out-of-range', () => {
    expect(() => circuitCellCenter(-1)).toThrow();
    expect(() => circuitCellCenter(CIRCUIT_SIZE)).toThrow();
  });

  it('home stretch cells for each color stay inside the viewBox', () => {
    for (const color of [Color.RED, Color.BLUE, Color.GREEN, Color.YELLOW]) {
      for (let i = 0; i < 8; i++) {
        const { x, y } = homeStretchCellCenter(color, i);
        expect(x).toBeGreaterThanOrEqual(0);
        expect(x).toBeLessThanOrEqual(BOARD_SIZE);
        expect(y).toBeGreaterThanOrEqual(0);
        expect(y).toBeLessThanOrEqual(BOARD_SIZE);
      }
    }
  });

  it('jails land in the corners consistent with the board image', () => {
    // Image layout (clockwise from bottom-right):
    //   RED bottom-right, GREEN top-right, BLUE top-left, YELLOW bottom-left.
    const red    = jailSlotCenter(Color.RED, 0);
    const green  = jailSlotCenter(Color.GREEN, 0);
    const blue   = jailSlotCenter(Color.BLUE, 0);
    const yellow = jailSlotCenter(Color.YELLOW, 0);
    expect(red.x).toBeGreaterThan(BOARD_CENTER);
    expect(red.y).toBeGreaterThan(BOARD_CENTER);
    expect(green.x).toBeGreaterThan(BOARD_CENTER);
    expect(green.y).toBeLessThan(BOARD_CENTER);
    expect(blue.x).toBeLessThan(BOARD_CENTER);
    expect(blue.y).toBeLessThan(BOARD_CENTER);
    expect(yellow.x).toBeLessThan(BOARD_CENTER);
    expect(yellow.y).toBeGreaterThan(BOARD_CENTER);
  });

  it('circuit salidas land in each color quadrant', () => {
    // pos 0 = RED, 17 = GREEN, 34 = BLUE, 51 = YELLOW.
    expect(circuitCellCenter(0).x).toBeGreaterThan(BOARD_CENTER);
    expect(circuitCellCenter(0).y).toBeGreaterThan(BOARD_CENTER);
    expect(circuitCellCenter(17).x).toBeGreaterThan(BOARD_CENTER);
    expect(circuitCellCenter(17).y).toBeLessThan(BOARD_CENTER);
    expect(circuitCellCenter(34).x).toBeLessThan(BOARD_CENTER);
    expect(circuitCellCenter(34).y).toBeLessThan(BOARD_CENTER);
    expect(circuitCellCenter(51).x).toBeLessThan(BOARD_CENTER);
    expect(circuitCellCenter(51).y).toBeGreaterThan(BOARD_CENTER);
  });
});
