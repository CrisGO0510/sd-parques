<template>
  <q-page class="q-pa-sm">
    <TurnBanner
      :is-my-turn="game.isMyTurn"
      :current-player-name="currentPlayerName"
      :phase="game.phase"
      :already-rolled-initial="alreadyRolledInitial"
    />

    <div class="row q-mt-md">
      <!-- Tablero -->
      <div class="col-12 col-md-8">
        <BoardCanvas :debug="debugBoard">
          <template #pieces>
            <PieceToken
              v-for="(piece, idx) in allPieces" :key="idx"
              :piece="piece.dto" :color="piece.color"
              :selectable="isSelectable(piece)"
              @click="onPieceClick(piece)"
            />
          </template>
        </BoardCanvas>
        <q-toggle v-model="debugBoard" label="Mostrar coordenadas (debug)" />
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

        <!-- Hint: when it's the player's turn in MOVING phase with legal
             moves available, the only way to progress is to click one of
             the highlighted pieces on the board. Make that obvious. -->
        <div v-if="showPieceHint" class="q-mt-md text-center">
          <div class="text-subtitle2">Elige una ficha para mover</div>
          <div class="text-caption text-grey">
            Las fichas disponibles brillan en dorado
          </div>
        </div>

        <q-btn disable class="q-mt-md full-width" label="Recomendación (pronto)" />

        <!-- Debug: quick inspection of the client's view of the game state.
             Leave this in for now; we can remove it once the flow feels
             solid and the team stops having to ask "what's going on?". -->
        <q-separator spaced />
        <div class="text-caption text-grey">
          <div>phase: {{ game.phase ?? '—' }}</div>
          <div>mi color: {{ game.myColor ?? '—' }}</div>
          <div>es mi turno: {{ game.isMyTurn }}</div>
          <div>moves disponibles: {{ game.availableMoves.length }}</div>
          <div>dados: {{ game.state?.pending_dice.join(', ') ?? '—' }}</div>
        </div>
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

const router = useRouter();
const game   = useGameStore();

const debugBoard = ref<boolean>(false);

interface PieceOwned { dto: PieceDto; color: Color; playerIndex: number }

// STATE_UPDATE / AVAILABLE_MOVES / ERROR and GAME_OVER's setWinner are
// handled in MainLayout (useAppEventSync). We only own GAME_OVER here for
// the navigation push — by the time this fires, game.winnerUsername is
// already set by the layout-level handler.
const { send } = useServerProtocol({
  [ServerEventType.GAME_OVER]: () => {
    void router.push(Route.END);
  },
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

// During SETUP each player rolls their own initial die independently of
// turn_order (which is still empty and only gets resolved after everyone
// has rolled). During ROLLING, only the current turn's player can roll.
const myPlayerIndex = computed<number>(() => {
  if (!game.state || game.myColor === null) return -1;
  return game.state.players.findIndex(p => p.color === game.myColor);
});

const alreadyRolledInitial = computed<boolean>(() => {
  if (!game.state) return false;
  const idx = myPlayerIndex.value;
  if (idx < 0) return false;
  // initial_rolls is Record<string, number> because JSON object keys are
  // always strings, even though Python stores dict[int, int].
  return String(idx) in game.state.initial_rolls;
});

const canRoll = computed<boolean>(() => {
  if (!game.state) return false;
  if (game.phase === GamePhase.SETUP) {
    return myPlayerIndex.value >= 0 && !alreadyRolledInitial.value;
  }
  return game.isMyTurn && game.phase === GamePhase.ROLLING;
});

const canSkip = computed<boolean>(() =>
  game.isMyTurn && game.phase === GamePhase.MOVING && game.availableMoves.length === 0
);

const showPieceHint = computed<boolean>(() =>
  game.isMyTurn && game.phase === GamePhase.MOVING && game.availableMoves.length > 0
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
