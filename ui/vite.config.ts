import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  const proxyUrl = new URL(env.API_PROXY_URL || 'http://127.0.0.1');
  proxyUrl.port = env.API_PROXY_PORT || '8000';
  return {
    plugins: [react()],
    server: {
      host: env.UI_HOST || '127.0.0.1',
      port: Number(env.UI_PORT || 5173),
      strictPort: true,
      proxy: { '/api': proxyUrl.origin },
    },
    test: { environment: 'jsdom', globals: true },
  };
});
