import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useConnectionStore } from './connection';
import type { ClientCommand, ServerEvent } from 'src/types/protocol';

export interface PlayerStats {
  id: number;
  username: string;
  games_played: number;
  games_won: number;
  win_percentage?: number;
}

export const useRankingStore = defineStore('ranking', () => {
  const connectionStore = useConnectionStore();
  
  const currentPlayer = ref<PlayerStats | null>(null);
  const ranking = ref<PlayerStats[]>([]);
  const isLoading = ref(false);

  // Compute win percentage
  const currentPlayerStats = computed(() => {
    if (!currentPlayer.value) return null;
    const percentage = currentPlayer.value.games_played > 0
      ? Math.round((currentPlayer.value.games_won / currentPlayer.value.games_played) * 100)
      : 0;
    return {
      ...currentPlayer.value,
      win_percentage: percentage,
    };
  });

  // Verify or register player on connection
  async function verifyPlayer(username: string): Promise<PlayerStats | null> {
    try {
      isLoading.value = true;
      
      // Send verify_player command
      const cmd: ClientCommand = {
        type: 'verify_player',
        username,
      };
      connectionStore.send(cmd as any);
      
      // Wait for response
      return new Promise((resolve, reject) => {
        const unsubscribe = connectionStore.onEvent((event: ServerEvent) => {
          if (event.type === 'player_verified') {
            const playerData: PlayerStats = {
              id: (event as any).player_id,
              username: (event as any).username,
              games_played: (event as any).games_played,
              games_won: (event as any).games_won,
            };
            currentPlayer.value = playerData;
            unsubscribe();
            resolve(playerData);
          } else if (event.type === 'error') {
            unsubscribe();
            reject(new Error((event as any).message));
          }
        });
        
        // Timeout after 5 seconds
        setTimeout(() => {
          unsubscribe();
          reject(new Error('Verification timeout'));
        }, 5000);
      });
    } finally {
      isLoading.value = false;
    }
  }

  // Fetch ranking
  async function fetchRanking(): Promise<PlayerStats[]> {
    try {
      isLoading.value = true;
      
      // Send get_ranking command
      const cmd: ClientCommand = {
        type: 'get_ranking',
      };
      connectionStore.send(cmd as any);
      
      // Wait for response
      return new Promise((resolve, reject) => {
        const unsubscribe = connectionStore.onEvent((event: ServerEvent) => {
          if (event.type === 'ranking_update') {
            const players = (event as any).players || [];
            ranking.value = players;
            unsubscribe();
            resolve(players);
          } else if (event.type === 'error') {
            unsubscribe();
            reject(new Error((event as any).message));
          }
        });
        
        // Timeout after 5 seconds
        setTimeout(() => {
          unsubscribe();
          reject(new Error('Ranking fetch timeout'));
        }, 5000);
      });
    } finally {
      isLoading.value = false;
    }
  }

  // Report a win
  async function reportWin(): Promise<PlayerStats | null> {
    if (!currentPlayer.value) {
      console.error('No current player set');
      return null;
    }
    
    try {
      const cmd: ClientCommand = {
        type: 'report_win',
        player_id: currentPlayer.value.id,
      };
      connectionStore.send(cmd as any);
      
      // Wait for response
      return new Promise((resolve, reject) => {
        const unsubscribe = connectionStore.onEvent((event: ServerEvent) => {
          if (event.type === 'stats_updated') {
            const updated: PlayerStats = {
              id: (event as any).player_id,
              username: currentPlayer.value?.username || '',
              games_played: (event as any).games_played,
              games_won: (event as any).games_won,
            };
            currentPlayer.value = updated;
            unsubscribe();
            resolve(updated);
          } else if (event.type === 'error') {
            unsubscribe();
            reject(new Error((event as any).message));
          }
        });
        
        // Timeout after 5 seconds
        setTimeout(() => {
          unsubscribe();
          reject(new Error('Report win timeout'));
        }, 5000);
      });
    } catch (error) {
      console.error('Error reporting win:', error);
      return null;
    }
  }

  return {
    currentPlayer,
    currentPlayerStats,
    ranking,
    isLoading,
    verifyPlayer,
    fetchRanking,
    reportWin,
  };
});
