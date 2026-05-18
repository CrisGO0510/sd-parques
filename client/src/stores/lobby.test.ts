import { setActivePinia, createPinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useLobbyStore } from './lobby';
import { Color } from 'src/types/domain';

describe('lobbyStore', () => {
  beforeEach(() => setActivePinia(createPinia()));

  it('starts empty', () => {
    const s = useLobbyStore();
    expect(s.players).toEqual([]);
    expect(s.isHost).toBe(false);
    expect(s.myColor).toBeNull();
  });

  it('canStart requires 2+ players all with color', () => {
    const s = useLobbyStore();
    expect(s.canStart).toBe(false);
    s.updateFromLobbyUpdate(
      [{ username: 'A', color: Color.RED, is_bot: false }],
      [Color.BLUE, Color.GREEN, Color.YELLOW],
    );
    expect(s.canStart).toBe(false);  // only 1 player
    s.updateFromLobbyUpdate(
      [
        { username: 'A', color: Color.RED, is_bot: false },
        { username: 'B', color: null,      is_bot: false },
      ],
      [Color.BLUE, Color.GREEN, Color.YELLOW],
    );
    expect(s.canStart).toBe(false);  // B has no color
    s.updateFromLobbyUpdate(
      [
        { username: 'A', color: Color.RED,  is_bot: false },
        { username: 'B', color: Color.BLUE, is_bot: false },
      ],
      [Color.GREEN, Color.YELLOW],
    );
    expect(s.canStart).toBe(true);
  });

  it('reset clears state', () => {
    const s = useLobbyStore();
    s.isHost = true;
    s.myColor = Color.RED;
    s.reset();
    expect(s.isHost).toBe(false);
    expect(s.myColor).toBeNull();
  });

  it('stores is_bot flag from lobby_update', () => {
    const s = useLobbyStore();
    s.updateFromLobbyUpdate(
      [
        { username: 'Cris',     color: Color.RED,  is_bot: false },
        { username: 'Bot Azul', color: Color.BLUE, is_bot: true  },
      ],
      [Color.GREEN, Color.YELLOW],
    );
    expect(s.players[1]!.is_bot).toBe(true);
    expect(s.players[0]!.is_bot).toBe(false);
  });
});
