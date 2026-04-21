import { onUnmounted } from 'vue';
import { useConnectionStore } from 'src/stores/connection';
import type { ClientCommand, ServerEvent, ServerEventType } from 'src/types/protocol';

type EventHandlers = {
  [K in ServerEventType]?: (event: Extract<ServerEvent, { type: K }>) => void;
};

export interface ServerProtocolHandle {
  send: (cmd: ClientCommand) => void;
}

export function useServerProtocol(handlers: EventHandlers): ServerProtocolHandle {
  const conn = useConnectionStore();

  const unsubscribe = conn.onEvent((event: ServerEvent) => {
    const handler = handlers[event.type];
    if (handler) {
      // Type assertion: the handler for each key K expects Extract<ServerEvent, { type: K }>,
      // which is exactly what we have when event.type === K.
      (handler as (e: ServerEvent) => void)(event);
    }
  });

  onUnmounted(unsubscribe);

  return { send: conn.send };
}
