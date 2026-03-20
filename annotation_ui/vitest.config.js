import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  esbuild: {
    loader: 'jsx',
    jsx: 'automatic',
    jsxImportSource: 'react',
    include: /src\/.*\.[jt]sx?$/,
    exclude: [],
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    css: true,
    exclude: ['**/node_modules/**', 'playwright/**'],
  },
});
