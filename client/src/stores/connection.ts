import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { ClientCommand, ServerEvent } from 'src/types/protocol';

export enum ConnectionStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING   = 'connecting',
  CONNECTED    = 'connected',
  ERROR        = 'error',
}

type EventHandler = (e: ServerEvent) => void;

export const useConnectionStore = defineStore('connection', () => {
  const status        = ref<ConnectionStatus>(ConnectionStatus.DISCONNECTED);
  const host          = ref<string>('localhost');
  const port          = ref<number>(5001);
  const username      = ref<string>('');
  const errorMessage  = ref<string | null>(null);

  // Not reactive on purpose — Vue doesn't need to observe these.
  let socket: WebSocket | null = null;
  const handlers: EventHandler[] = [];

  function connect(h: string, p: number, u: string): Promise<void> {
    host.value = h;
    port.value = p;
    username.value = u;
    status.value = ConnectionStatus.CONNECTING;
    errorMessage.value = null;

    return new Promise((resolve, reject) => {
      const ws = new WebSocket(`ws://${h}:${p}`);
      socket = ws;
      ws.onopen = () => {
        status.value = ConnectionStatus.CONNECTED;
        resolve();
      };
      ws.onerror = () => {
        status.value = ConnectionStatus.ERROR;
        errorMessage.value = 'connection error';
        reject(new Error('connection error'));
      };
      ws.onclose = () => {
        status.value = ConnectionStatus.DISCONNECTED;
      };
      ws.onmessage = (evt: MessageEvent<string>) => {
        const parsed = JSON.parse(evt.data) as ServerEvent;
        for (const h of handlers) h(parsed);
      };
    });
  }

  // WebSocket.OPEN === 1 per spec; use literal so mocks work in tests.
  const WS_OPEN = 1;

  function send(cmd: ClientCommand): void {
    if (!socket || socket.readyState !== WS_OPEN) {
      throw new Error('socket not open');
    }
    socket.send(JSON.stringify(cmd));
  }

  function onEvent(handler: EventHandler): () => void {
    handlers.push(handler);
    return () => {
      const i = handlers.indexOf(handler);
      if (i >= 0) handlers.splice(i, 1);
    };
  }

  function disconnect(): void {
    if (socket) {
      socket.close();
      socket = null;
    }
    // Do NOT clear handlers here — they belong to the components that
    // registered them (MainLayout, pages). Each component's onUnmounted()
    // unsubscribes its own handler. Clearing indiscriminately would drop the
    // layout-level handler that must survive a disconnect/reconnect cycle.
    status.value = ConnectionStatus.DISCONNECTED;
  }

  return { status, host, port, username, errorMessage,
           connect, send, onEvent, disconnect };
});
