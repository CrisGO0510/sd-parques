import { ErrorCode } from './protocol';

const FRIENDLY_MESSAGES: Partial<Record<ErrorCode, string>> = {
  [ErrorCode.DUPLICATE_PLAYER]: 'Ese nombre ya está en uso',
  [ErrorCode.LOBBY_FULL]: 'La sala ya tiene 2 jugadores',
};

export function friendlyErrorMessage(code: ErrorCode, fallback: string): string {
  return FRIENDLY_MESSAGES[code] ?? fallback;
}
