declare module 'quasar' {
  export interface QuasarNotifyOptions {
    color?: string;
    icon?: string;
    message?: string;
    position?: string;
    timeout?: number;
  }

  export interface QuasarInstance {
    notify: (options: QuasarNotifyOptions) => void;
  }

  export function useQuasar(): QuasarInstance;
}