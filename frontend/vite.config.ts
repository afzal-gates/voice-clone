import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const isDev = mode === 'development';

  return {
    plugins: [react()],

    // Development server configuration
    server: {
      port: 5173,
      proxy: {
        // Proxy API calls to FastAPI backend
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
        // Proxy WebSocket connections
        '/ws': {
          target: 'ws://localhost:8000',
          ws: true,
        },
      },
    },

    // Production build configuration
    build: {
      outDir: '../app/static',
      emptyOutDir: true,
      sourcemap: !isDev,
      rollupOptions: {
        output: {
          // Manual code splitting for better caching
          manualChunks: {
            vendor: ['react', 'react-dom'],
            store: ['zustand'],
          },
        },
      },
    },

    // Path aliases for cleaner imports
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@components': path.resolve(__dirname, './src/components'),
        '@features': path.resolve(__dirname, './src/features'),
        '@hooks': path.resolve(__dirname, './src/hooks'),
        '@services': path.resolve(__dirname, './src/services'),
        '@store': path.resolve(__dirname, './src/store'),
        '@types': path.resolve(__dirname, './src/types'),
        '@utils': path.resolve(__dirname, './src/utils'),
        '@config': path.resolve(__dirname, './src/config'),
        '@styles': path.resolve(__dirname, './src/styles'),
      },
    },

    // Base path for assets
    base: isDev ? '/' : '/static/',
  };
});
