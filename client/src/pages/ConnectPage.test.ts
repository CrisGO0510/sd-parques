import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import ConnectPage from './ConnectPage.vue';
import { installMockWebSocket } from 'src/test-utils/mockWebSocket';
import type { MockWebSocket } from 'src/test-utils/mockWebSocket';

const pushSpy = vi.fn();
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
}));

const notifySpy = vi.fn();
vi.mock('quasar', () => ({
  useQuasar: () => ({ notify: notifySpy }),
}));

describe('ConnectPage', () => {
  let mock: { restore: () => void; instances: MockWebSocket[] };

  beforeEach(() => {
    setActivePinia(createPinia());
    mock = installMockWebSocket();
    pushSpy.mockClear();
    notifySpy.mockClear();
    const store: Record<string, string> = {};
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => { store[k] = v; },
      removeItem: (k: string) => { delete store[k]; },
      clear: () => { for (const k of Object.keys(store)) delete store[k]; },
    });
  });
  afterEach(() => mock.restore());

  function mountPage(): ReturnType<typeof mount> {
    return mount(ConnectPage, {
      global: {
        stubs: {
          'q-page':         { template: '<div><slot/></div>' },
          'q-card':         { template: '<div><slot/></div>' },
          'q-card-section': { template: '<div><slot/></div>' },
          'q-card-actions': { template: '<div><slot/></div>' },
          'q-input':        { template: '<div><slot/></div>' },
          'q-btn': {
            props: ['label', 'loading'],
            template: '<button :data-loading="loading" @click="$emit(\'click\')">{{ label }}</button>',
            emits: ['click'],
          },
        },
      },
    });
  }

  it('clears connecting state when server rejects join with DUPLICATE_PLAYER', async () => {
    const wrapper = mountPage();

    await wrapper.find('button').trigger('click');
    // While the WS is opening the button is in loading state.
    expect(wrapper.find('button').attributes('data-loading')).toBe('true');

    const ws = mock.instances[0]!;
    ws.simulateOpen();
    await flushPromises();

    // The page sent a join command and is now waiting for welcome/error.
    expect(ws.sent.some((s) => s.includes('"type":"join"'))).toBe(true);
    expect(wrapper.find('button').attributes('data-loading')).toBe('true');

    // Server rejects the join — username already taken.
    ws.simulateMessage(
      '{"type":"error","code":"DUPLICATE_PLAYER","message":"duplicate name: alice"}',
    );
    await flushPromises();

    // The button must NOT be stuck loading — user has to be able to retry.
    expect(wrapper.find('button').attributes('data-loading')).toBe('false');
    // And we must NOT have navigated away from ConnectPage.
    expect(pushSpy).not.toHaveBeenCalled();
  });
});
