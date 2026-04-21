import { createApp } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useServerProtocol } from './useServerProtocol';
import { ServerEventType, ClientCommandType } from 'src/types/protocol';
import { useConnectionStore } from 'src/stores/connection';
import { installMockWebSocket } from 'src/test-utils/mockWebSocket';
import type { MockWebSocket } from 'src/test-utils/mockWebSocket';

describe('useServerProtocol', () => {
  let mock: { restore: () => void; instances: MockWebSocket[] };
  let pinia: ReturnType<typeof createPinia>;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    mock = installMockWebSocket();
  });
  afterEach(() => mock.restore());

  it('fires the registered handler when a typed event arrives', async () => {
    const store = useConnectionStore();
    const p = store.connect('localhost', 5001, 'A');
    mock.instances[0]!.simulateOpen();
    await p;

    const welcomeSpy = vi.fn();
    const sendSpy    = vi.fn();

    // Tiny Vue app so onUnmounted lifecycle works.
    const app = createApp({
      setup() {
        const { send } = useServerProtocol({
          [ServerEventType.WELCOME]: welcomeSpy,
        });
        // Trigger and assert via vitest spies (callbacks run sync).
        sendSpy.mockImplementation(send);
        return () => null;
      },
    });
    app.use(pinia);  // use the same pinia that was set active in beforeEach
    const el = document.createElement('div');
    app.mount(el);

    mock.instances[0]!.simulateMessage('{"type":"welcome","username":"A","is_host":true}');
    expect(welcomeSpy).toHaveBeenCalledWith({
      type: ServerEventType.WELCOME,
      username: 'A',
      is_host: true,
    });

    sendSpy({ type: ClientCommandType.ROLL_DICE });
    expect(mock.instances[0]!.sent).toContain('{"type":"roll_dice"}');

    app.unmount();
  });
});
