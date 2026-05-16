import type {
  Color,
  GameStateDto,
  LobbyPlayerDto,
  MoveDto,
  MoveResultDto,
  MoveAction,
} from './domain';

export enum ClientCommandType {
  JOIN = 'join',
  SELECT_COLOR = 'select_color',
  START_GAME = 'start_game',
  ROLL_INITIAL = 'roll_initial',
  ROLL_DICE = 'roll_dice',
  MOVE_PIECE = 'move_piece',
  SKIP_TURN = 'skip_turn',
  CROWN_PIECE = 'crown_piece',
  LEAVE = 'leave',
  CHAT = 'chat',
  VERIFY_PLAYER = 'verify_player',
  GET_RANKING = 'get_ranking',
  REPORT_WIN = 'report_win',
  TIME_RESPONSE = 'time_response',
}

export enum ServerEventType {
  WELCOME = 'welcome',
  LOBBY_UPDATE = 'lobby_update',
  GAME_STARTED = 'game_started',
  STATE_UPDATE = 'state_update',
  INITIAL_ROLL = 'initial_roll',
  DICE_RESULT = 'dice_result',
  AVAILABLE_MOVES = 'available_moves',
  RECOMMENDATION = 'recommendation',
  MOVE_APPLIED = 'move_applied',
  GAME_OVER = 'game_over',
  ERROR = 'error',
  CHAT = 'chat',
  PLAYER_VERIFIED = 'player_verified',
  RANKING_UPDATE = 'ranking_update',
  STATS_UPDATED = 'stats_updated',
  TIME_REQUEST = 'time_request',
  TIME_ADJUST  = 'time_adjust',
}

export enum ErrorCode {
  BAD_MESSAGE = 'BAD_MESSAGE',
  NOT_AUTHENTICATED = 'NOT_AUTHENTICATED',
  DUPLICATE_PLAYER = 'DUPLICATE_PLAYER',
  WRONG_PHASE = 'WRONG_PHASE',
  INVALID_MOVE = 'INVALID_MOVE',
  FORBIDDEN = 'FORBIDDEN',
  GAME_ENDED = 'GAME_ENDED',
  DB_ERROR = 'DB_ERROR',
}

export type ClientCommand =
  | { type: ClientCommandType.JOIN; username: string }
  | { type: ClientCommandType.SELECT_COLOR; color: Color }
  | { type: ClientCommandType.START_GAME }
  | { type: ClientCommandType.ROLL_INITIAL }
  | { type: ClientCommandType.ROLL_DICE }
  | {
      type: ClientCommandType.MOVE_PIECE;
      piece_index: number;
      dice_value: number;
      action: MoveAction;
    }
  | { type: ClientCommandType.SKIP_TURN }
  | { type: ClientCommandType.CROWN_PIECE; piece_index: number }
  | { type: ClientCommandType.LEAVE }
  | { type: ClientCommandType.CHAT; message: string }
  | { type: ClientCommandType.VERIFY_PLAYER; username: string }
  | { type: ClientCommandType.GET_RANKING }
  | { type: ClientCommandType.REPORT_WIN; player_id: number }
  | { type: ClientCommandType.TIME_RESPONSE; client_time: number };

export type ServerEvent =
  | { type: ServerEventType.WELCOME; username: string; is_host: boolean }
  | {
      type: ServerEventType.LOBBY_UPDATE;
      players: LobbyPlayerDto[];
      available_colors: Color[];
    }
  | { type: ServerEventType.GAME_STARTED }
  | { type: ServerEventType.STATE_UPDATE; state: GameStateDto }
  | {
      type: ServerEventType.INITIAL_ROLL;
      player_index: number;
      username: string;
      d1: number;
      d2: number;
      total: number;
    }
  | {
      type: ServerEventType.DICE_RESULT;
      player_index: number;
      d1: number;
      d2: number;
      is_pair: boolean;
    }
  | { type: ServerEventType.AVAILABLE_MOVES; moves: MoveDto[] }
  | { type: ServerEventType.RECOMMENDATION; piece_index: number; action: string; dice_value: number }
  | { type: ServerEventType.CHAT; username: string; message: string }
  | { type: ServerEventType.MOVE_APPLIED; move: MoveDto; result: MoveResultDto }
  | {
      type: ServerEventType.GAME_OVER;
      winner_index: number | null;
      winner_username: string | null;
    }
  | { type: ServerEventType.ERROR; code: ErrorCode; message: string }
  | {
      type: ServerEventType.PLAYER_VERIFIED;
      player_id: number;
      username: string;
      games_played: number;
      games_won: number;
    }
  | {
      type: ServerEventType.RANKING_UPDATE;
      players: Array<{
        id: number;
        username: string;
        games_played: number;
        games_won: number;
        win_percentage?: number;
      }>;
    }
  | {
      type: ServerEventType.STATS_UPDATED;
      player_id: number;
      games_played: number;
      games_won: number;
    }
    | { type: ServerEventType.TIME_REQUEST; server_time: number }
  | { type: ServerEventType.TIME_ADJUST;  adjust_ms: number };

export function assertNever(x: never): never {
  throw new Error(`unexpected value in exhaustive switch: ${JSON.stringify(x)}`);
}
