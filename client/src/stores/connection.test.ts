import { setActivePinia, createPinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { ConnectionStatus, useConnectionStore } from './connection';
import { ClientCommandType, ServerEventType } from 'src/types/protocol';
import { installMockWebSocket } from 'src/test-utils/mockWebSocket';
import type { MockWebSocket } from 'src/test-utils/mockWebSocket';

describe('connectionStore', () => {
  let mock: { restore: () => void; instances: MockWebSocket[] };

  beforeEach(() => {
    setActivePinia(createPinia());
    mock = installMockWebSocket();
  });

  afterEach(() => mock.restore());

  it('starts disconnected', () => {
    const store = useConnectionStore();
    expect(store.status).toBe(ConnectionStatus.DISCONNECTED);
  });

  it('connect() sets status to CONNECTED after onopen', async () => {
    const store = useConnectionStore();
    const promise = store.connect('localhost', 5001, 'Alice');
    const ws = mock.instances[0]!;
    ws.simulateOpen();
    await promise;
    expect(store.status).toBe(ConnectionStatus.CONNECTED);
    expect(store.host).toBe('localhost');
    expect(store.port).toBe(5001);
    expect(store.username).toBe('Alice');
  });

  it('builds wss:// when given a full wss:// URL (port ignored)', () => {
    const store = useConnectionStore();
    void store.connect('wss://sd-parques-web.onrender.com', 443, 'A');
    expect(mock.instances[0]!.url).toBe('wss://sd-parques-web.onrender.com');
  });

  it('builds wss:// for a bare host on port 443', () => {
    const store = useConnectionStore();
    void store.connect('sd-parques-web.onrender.com', 443, 'A');
    expect(mock.instances[0]!.url).toBe('wss://sd-parques-web.onrender.com:443');
  });

  it('builds ws:// for a local host/port', () => {
    const store = useConnectionStore();
    void store.connect('localhost', 5001, 'A');
    expect(mock.instances[0]!.url).toBe('ws://localhost:5001');
  });

  it('send() writes serialized JSON to the socket', async () => {
    const store = useConnectionStore();
    const promise = store.connect('localhost', 5001, 'Alice');
    mock.instances[0]!.simulateOpen();
    await promise;
    store.send({ type: ClientCommandType.JOIN, username: 'Alice' });
    expect(mock.instances[0]!.sent).toEqual(['{"type":"join","username":"Alice"}']);
  });

  it('onEvent() fires for incoming messages', async () => {
    const store = useConnectionStore();
    const promise = store.connect('localhost', 5001, 'Alice');
    mock.instances[0]!.simulateOpen();
    await promise;

    let received: unknown = null;
    store.onEvent((e) => { received = e; });
    mock.instances[0]!.simulateMessage('{"type":"welcome","username":"Alice","is_host":true}');
    expect(received).toEqual({
      type: ServerEventType.WELCOME,
      username: 'Alice',
      is_host: true,
    });
  });

  it('disconnect() transitions back to DISCONNECTED', async () => {
    const store = useConnectionStore();
    const promise = store.connect('localhost', 5001, 'Alice');
    mock.instances[0]!.simulateOpen();
    await promise;
    store.disconnect();
    expect(store.status).toBe(ConnectionStatus.DISCONNECTED);
  });
});
