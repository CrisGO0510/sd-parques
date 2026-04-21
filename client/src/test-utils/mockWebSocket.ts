export enum MockWSState {
  CONNECTING = 0,
  OPEN       = 1,
  CLOSING    = 2,
  CLOSED     = 3,
}

export class MockWebSocket {
  readyState: MockWSState = MockWSState.CONNECTING;
  onopen:    (() => void) | null = null;
  onclose:   (() => void) | null = null;
  onerror:   ((e: unknown) => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  sent: string[] = [];

  constructor(public url: string) { /* defer open */ }

  // Test helpers — NOT part of the real WebSocket API
  simulateOpen(): void {
    this.readyState = MockWSState.OPEN;
    this.onopen?.();
  }

  simulateMessage(data: string): void {
    this.onmessage?.({ data });
  }

  simulateClose(): void {
    this.readyState = MockWSState.CLOSED;
    this.onclose?.();
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.readyState = MockWSState.CLOSED;
    this.onclose?.();
  }
}

export function installMockWebSocket(): { restore: () => void; instances: MockWebSocket[] } {
  const originalWS = globalThis.WebSocket;
  const instances: MockWebSocket[] = [];
  class TrackedMock extends MockWebSocket {
    constructor(url: string) {
      super(url);
      instances.push(this);
    }
  }
  (globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket = TrackedMock as unknown as typeof WebSocket;
  return {
    restore: () => { (globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket = originalWS; },
    instances,
  };
}
