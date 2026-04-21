import { describe, expect, it } from 'vitest';
import { Color } from 'src/types/domain';
import {
  BOARD_SIZE,
  circuitCellCenter,
  goalCenter,
  homeStretchCellCenter,
  jailSlotCenter,
} from './useBoardGeometry';

describe('useBoardGeometry', () => {
  it('goal center is at (300, 300)', () => {
    expect(goalCenter()).toEqual({ x: 300, y: 300 });
  });

  it('circuit cells are all within the viewBox', () => {
    for (let p = 0; p < 96; p++) {
      const { x, y } = circuitCellCenter(p);
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThanOrEqual(BOARD_SIZE);
      expect(y).toBeGreaterThanOrEqual(0);
      expect(y).toBeLessThanOrEqual(BOARD_SIZE);
    }
  });

  it('circuitCellCenter throws for out-of-range', () => {
    expect(() => circuitCellCenter(-1)).toThrow();
    expect(() => circuitCellCenter(96)).toThrow();
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

  it('jail slots distribute into 4 corners', () => {
    const red    = jailSlotCenter(Color.RED, 0);
    const blue   = jailSlotCenter(Color.BLUE, 0);
    const green  = jailSlotCenter(Color.GREEN, 0);
    const yellow = jailSlotCenter(Color.YELLOW, 0);
    // Red top-left should have small x and y.
    expect(red.x).toBeLessThan(BOARD_SIZE / 2);
    expect(red.y).toBeLessThan(BOARD_SIZE / 2);
    // Blue top-right.
    expect(blue.x).toBeGreaterThan(BOARD_SIZE / 2);
    expect(blue.y).toBeLessThan(BOARD_SIZE / 2);
    // Green bottom-right.
    expect(green.x).toBeGreaterThan(BOARD_SIZE / 2);
    expect(green.y).toBeGreaterThan(BOARD_SIZE / 2);
    // Yellow bottom-left.
    expect(yellow.x).toBeLessThan(BOARD_SIZE / 2);
    expect(yellow.y).toBeGreaterThan(BOARD_SIZE / 2);
  });
});
