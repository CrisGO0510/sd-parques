import type { GameStateDto, PieceDto, PlayerDto } from 'src/types/domain';
import { Color, GamePhase, PieceState } from 'src/types/domain';

export function makePiece(overrides: Partial<PieceDto> = {}): PieceDto {
  return {
    index: 0,
    state: PieceState.IN_JAIL,
    circuit_position: null,
    home_stretch_position: null,
    ...overrides,
  };
}

export function makePlayer(overrides: Partial<PlayerDto> = {}): PlayerDto {
  return {
    name: 'Alice',
    color: Color.RED,
    pieces: [
      makePiece({ index: 0 }),
      makePiece({ index: 1 }),
      makePiece({ index: 2 }),
      makePiece({ index: 3 }),
    ],
    ...overrides,
  };
}

export function makeGameState(overrides: Partial<GameStateDto> = {}): GameStateDto {
  return {
    players: [
      makePlayer({ name: 'Alice', color: Color.RED }),
      makePlayer({ name: 'Bob', color: Color.BLUE }),
    ],
    phase: GamePhase.SETUP,
    turn_order: [],
    current_turn_index: 0,
    pending_dice: [],
    initial_rolls: {},
    initial_rolls_remaining: 0,
    consecutive_pairs: 0,
    winner: null,
    ...overrides,
  };
}
