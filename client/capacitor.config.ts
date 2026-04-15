import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.parques.distribuido',
  appName: 'Parques Distribuido',
  webDir: 'dist/spa',
  server: {
    androidScheme: 'https',
  },
};

export default config;
