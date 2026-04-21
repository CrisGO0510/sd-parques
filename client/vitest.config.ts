import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      src:        fileURLToPath(new URL('./src', import.meta.url)),
      components: fileURLToPath(new URL('./src/components', import.meta.url)),
      stores:     fileURLToPath(new URL('./src/stores', import.meta.url)),
      pages:      fileURLToPath(new URL('./src/pages', import.meta.url)),
      layouts:    fileURLToPath(new URL('./src/layouts', import.meta.url)),
      boot:       fileURLToPath(new URL('./src/boot', import.meta.url)),
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    passWithNoTests: true,
    coverage: {
      provider: 'v8',
      include: ['src/stores/**', 'src/composables/**'],
      reporter: ['text', 'html'],
    },
  },
});
