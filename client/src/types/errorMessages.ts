import { ErrorCode } from './protocol';

const FRIENDLY_MESSAGES: Partial<Record<ErrorCode, string>> = {
  [ErrorCode.DUPLICATE_PLAYER]: 'Ese nombre ya está en uso',
};

export function friendlyErrorMessage(code: ErrorCode, fallback: string): string {
  return FRIENDLY_MESSAGES[code] ?? fallback;
}
