import { setActivePinia, createPinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useGameStore } from './game';
import { Color, GamePhase } from 'src/types/domain';
import { makeGameState } from 'src/test-utils/factories';

describe('gameStore', () => {
  beforeEach(() => setActivePinia(createPinia()));

  it('starts with no state', () => {
    const s = useGameStore();
    expect(s.state).toBeNull();
    expect(s.isMyTurn).toBe(false);
    expect(s.phase).toBeNull();
  });

  it('isMyTurn is true when turn_order[current_turn_index] is my color', () => {
    const s = useGameStore();
    s.myColor = Color.RED;
    // Alice (RED) is players[0], Bob (BLUE) is players[1]. turn_order: [0, 1].
    s.updateFromStateUpdate(makeGameState({
      phase: GamePhase.ROLLING,
      turn_order: [0, 1],
      current_turn_index: 0,
    }));
    expect(s.isMyTurn).toBe(true);
    s.updateFromStateUpdate(makeGameState({
      phase: GamePhase.ROLLING,
      turn_order: [0, 1],
      current_turn_index: 1,
    }));
    expect(s.isMyTurn).toBe(false);
  });

  it('phase reflects state.phase', () => {
    const s = useGameStore();
    s.updateFromStateUpdate(makeGameState({ phase: GamePhase.MOVING, pending_dice: [3, 5] }));
    expect(s.phase).toBe(GamePhase.MOVING);
    expect(s.dice).toEqual([3, 5]);
  });

  it('setWinner updates winnerUsername', () => {
    const s = useGameStore();
    s.setWinner('Alice');
    expect(s.winnerUsername).toBe('Alice');
  });

  it('reset clears everything', () => {
    const s = useGameStore();
    s.myColor = Color.RED;
    s.setWinner('Alice');
    s.updateFromStateUpdate(makeGameState());
    s.reset();
    expect(s.state).toBeNull();
    expect(s.myColor).toBeNull();
    expect(s.winnerUsername).toBeNull();
  });
});
