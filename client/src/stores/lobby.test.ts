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

  it('canStart requires >=1 human and every player to have a color', () => {
    const s = useLobbyStore();
    expect(s.canStart).toBe(false);
    // 2 bots con color + 1 humano sin color -> false
    s.updateFromLobbyUpdate(
      [
        { username: 'Camila', color: Color.GREEN,  is_bot: true  },
        { username: 'Bryan',  color: Color.YELLOW, is_bot: true  },
        { username: 'A',      color: null,         is_bot: false },
      ],
      [Color.RED, Color.BLUE],
    );
    expect(s.canStart).toBe(false);
    // humano con color -> true (1 humano basta)
    s.updateFromLobbyUpdate(
      [
        { username: 'Camila', color: Color.GREEN,  is_bot: true  },
        { username: 'Bryan',  color: Color.YELLOW, is_bot: true  },
        { username: 'A',      color: Color.RED,    is_bot: false },
      ],
      [Color.BLUE],
    );
    expect(s.canStart).toBe(true);
  });

  it('canStart is false when there are only bots', () => {
    const s = useLobbyStore();
    s.updateFromLobbyUpdate(
      [
        { username: 'Camila', color: Color.GREEN,  is_bot: true },
        { username: 'Bryan',  color: Color.YELLOW, is_bot: true },
      ],
      [Color.RED, Color.BLUE],
    );
    expect(s.canStart).toBe(false);
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
        { username: 'Cris',   color: Color.RED,   is_bot: false },
        { username: 'Camila', color: Color.GREEN, is_bot: true  },
      ],
      [Color.BLUE],
    );
    expect(s.players[1]!.is_bot).toBe(true);
    expect(s.players[0]!.is_bot).toBe(false);
  });
});
