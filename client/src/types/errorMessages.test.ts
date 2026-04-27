import { describe, expect, it } from 'vitest';
import { ErrorCode } from './protocol';
import { friendlyErrorMessage } from './errorMessages';

describe('friendlyErrorMessage', () => {
  it('maps DUPLICATE_PLAYER to a user-friendly Spanish message', () => {
    expect(friendlyErrorMessage(ErrorCode.DUPLICATE_PLAYER, 'duplicate name: alice'))
      .toBe('Ese nombre ya está en uso');
  });

  it('falls back to the server message for codes without a friendly mapping', () => {
    expect(friendlyErrorMessage(ErrorCode.BAD_MESSAGE, 'malformed json'))
      .toBe('malformed json');
  });
});
