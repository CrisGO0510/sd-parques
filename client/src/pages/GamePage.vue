<template>
  <q-page class="q-pa-sm">
    <TurnBanner :is-my-turn="game.isMyTurn" :current-player-name="currentPlayerName" />

    <div class="row q-mt-md">
      <!-- Tablero -->
      <div class="col-12 col-md-8">
        <BoardCanvas>
          <template #pieces>
            <PieceToken
              v-for="(piece, idx) in allPieces" :key="idx"
              :piece="piece.dto" :color="piece.color"
              :selectable="isSelectable(piece)"
              @click="onPieceClick(piece)"
            />
          </template>
        </BoardCanvas>
      </div>

      <!-- Panel lateral -->
      <div class="col-12 col-md-4 q-pl-md">
        <PlayerList
          v-if="game.state"
          :players="game.state.players"
          :current-turn-index="currentTurnIndex"
        />
        <q-separator spaced />
        <DiceRoller
          :d1="game.dice?.[0] ?? null"
          :d2="game.dice?.[1] ?? null"
          :can-roll="canRoll"
          @roll="onRoll"
        />
        <q-btn v-if="canSkip" class="q-mt-md full-width" label="Pasar turno" @click="onSkip" />
        <q-btn disable class="q-mt-md full-width" label="Recomendación (pronto)" />
      </div>
    </div>

    <!-- Dialog: Crowning (triple pair) -->
    <q-dialog :model-value="game.phase === GamePhase.CROWNING && game.isMyTurn" persistent>
      <q-card>
        <q-card-section class="text-center">
          <div class="text-h6">¡Triple par!</div>
          <div>Elige la ficha que quieres coronar</div>
        </q-card-section>
        <q-card-actions align="center">
          <q-btn
            v-for="p in crownablePieces" :key="p.index"
            color="primary" :label="`Ficha ${p.index + 1}`"
            @click="onCrownPiece(p.index)"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Dialog: Choose die when piece has multiple options -->
    <q-dialog :model-value="dieChoice !== null" persistent>
      <q-card v-if="dieChoice">
        <q-card-section>
          ¿Usar el {{ dieChoice.options[0] }} o el {{ dieChoice.options[1] }}?
        </q-card-section>
        <q-card-actions align="center">
          <q-btn
            v-for="die in dieChoice.options" :key="die"
            color="primary" :label="String(die)"
            @click="onDieChosen(die)"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';

import BoardCanvas from 'components/BoardCanvas.vue';
import PieceToken from 'components/PieceToken.vue';
import DiceRoller from 'components/DiceRoller.vue';
import PlayerList from 'components/PlayerList.vue';
import TurnBanner from 'components/TurnBanner.vue';

import { useGameStore } from 'src/stores/game';
import { useServerProtocol } from 'src/composables/useServerProtocol';
import { ClientCommandType, ServerEventType } from 'src/types/protocol';
import { GamePhase, PieceState } from 'src/types/domain';
import type { Color, PieceDto, MoveDto } from 'src/types/domain';
import { Route } from 'src/router/routes';

const $q     = useQuasar();
const router = useRouter();
const game   = useGameStore();

interface PieceOwned { dto: PieceDto; color: Color; playerIndex: number }

const { send } = useServerProtocol({
  [ServerEventType.STATE_UPDATE]:    (e) => game.updateFromStateUpdate(e.state),
  [ServerEventType.AVAILABLE_MOVES]: (e) => game.setAvailableMoves(e.moves),
  [ServerEventType.GAME_OVER]:       (e) => {
    game.setWinner(e.winner_username);
    void router.push(Route.END);
  },
  [ServerEventType.ERROR]: (e) => $q.notify({ color: 'negative', message: e.message }),
});

const allPieces = computed<PieceOwned[]>(() => {
  if (!game.state) return [];
  const out: PieceOwned[] = [];
  for (let pIdx = 0; pIdx < game.state.players.length; pIdx++) {
    const player = game.state.players[pIdx]!;
    for (const piece of player.pieces) {
      out.push({ dto: piece, color: player.color, playerIndex: pIdx });
    }
  }
  return out;
});

const currentTurnIndex = computed<number>(() => {
  const st = game.state;
  if (!st || st.turn_order.length === 0) return -1;
  return st.turn_order[st.current_turn_index] ?? -1;
});

const currentPlayerName = computed<string | null>(() => {
  const idx = currentTurnIndex.value;
  return idx >= 0 ? game.state?.players[idx]?.name ?? null : null;
});

function isSelectable(p: PieceOwned): boolean {
  if (!game.isMyTurn) return false;
  if (p.color !== game.myColor) return false;
  return game.availableMoves.some(m => m.piece_index === p.dto.index);
}

const canRoll = computed<boolean>(() =>
  game.isMyTurn && (game.phase === GamePhase.ROLLING || game.phase === GamePhase.SETUP)
);

const canSkip = computed<boolean>(() =>
  game.isMyTurn && game.phase === GamePhase.MOVING && game.availableMoves.length === 0
);

function onRoll(): void {
  if (game.phase === GamePhase.SETUP) {
    send({ type: ClientCommandType.ROLL_INITIAL });
  } else {
    send({ type: ClientCommandType.ROLL_DICE });
  }
}

function onSkip(): void {
  send({ type: ClientCommandType.SKIP_TURN });
}

const crownablePieces = computed<PieceDto[]>(() => {
  if (!game.state || game.myColor === null) return [];
  const me = game.state.players.find(p => p.color === game.myColor);
  return me ? me.pieces.filter(pc => pc.state !== PieceState.CROWNED) : [];
});

function onCrownPiece(piece_index: number): void {
  send({ type: ClientCommandType.CROWN_PIECE, piece_index });
}

// Die-choice handling: if a piece has multiple moves with different dice, ask.
interface DieChoice { pieceIndex: number; options: number[] }
const dieChoice = ref<DieChoice | null>(null);

function onPieceClick(p: PieceOwned): void {
  const matches = game.availableMoves.filter(m => m.piece_index === p.dto.index);
  if (matches.length === 1) {
    applyMove(matches[0]!);
  } else if (matches.length > 1) {
    const uniqueDice = [...new Set(matches.map(m => m.dice_value))];
    if (uniqueDice.length === 1) {
      // Multiple moves but same die value — take the first (semantically identical).
      applyMove(matches[0]!);
    } else {
      dieChoice.value = { pieceIndex: p.dto.index, options: uniqueDice };
    }
  }
}

function onDieChosen(die: number): void {
  if (!dieChoice.value) return;
  const move = game.availableMoves.find(m =>
    m.piece_index === dieChoice.value!.pieceIndex && m.dice_value === die
  );
  dieChoice.value = null;
  if (move) applyMove(move);
}

function applyMove(move: MoveDto): void {
  send({
    type: ClientCommandType.MOVE_PIECE,
    piece_index: move.piece_index,
    dice_value: move.dice_value,
    action: move.action,
  });
}
</script>
