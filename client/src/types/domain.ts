// Los valores string deben coincidir EXACTAMENTE con core/entities.py
// porque viajan por el wire sin transformación (snake_case en DTOs).

export enum Color {
  RED = 'red',
  BLUE = 'blue',
  GREEN = 'green',
  YELLOW = 'yellow',
}

export enum PieceState {
  IN_JAIL = 'in_jail',
  ON_BOARD = 'on_board',
  IN_HOME_STRETCH = 'in_home_stretch',
  CROWNED = 'crowned',
}

export enum GamePhase {
  SETUP = 'setup',
  ROLLING = 'rolling',
  MOVING = 'moving',
  CROWNING = 'crowning',
  FINISHED = 'finished',
}

export enum MoveAction {
  EXIT_JAIL = 'exit_jail',
  ADVANCE = 'advance',
  CAPTURE = 'capture',
  ENTER_HOME_STRETCH = 'enter_home_stretch',
  REACH_GOAL = 'reach_goal',
}

export interface PieceDto {
  index: number;
  state: PieceState;
  circuit_position: number | null;
  home_stretch_position: number | null;
}

export interface PlayerDto {
  name: string;
  color: Color;
  pieces: PieceDto[];
}

export interface GameStateDto {
  players: PlayerDto[];
  phase: GamePhase;
  turn_order: number[];
  current_turn_index: number;
  pending_dice: number[];
  initial_rolls: Record<string, number>;
  initial_rolls_remaining: number;
  consecutive_pairs: number;
  winner: number | null;
  disconnected_colors: Color[];
}

export interface MoveDto {
  piece_index: number;
  dice_value: number;
  action: MoveAction;
}

export interface MoveResultDto {
  action: MoveAction;
  reached_goal: boolean;
  captured: PieceDto[];
}

export interface LobbyPlayerDto {
  username: string;
  color: Color | null;
}
