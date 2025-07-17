import { defineConfig } from 'vite';
import { resolve } from 'path';
import dts from 'vite-plugin-dts';

export default defineConfig({
  plugins: [
    dts({
      insertTypesEntry: true,
      rollupTypes: true,
    }),
  ],

  build: {
    lib: {
      entry: resolve(__dirname, 'src/client/index.ts'),
      name: 'AgentClient',
      fileName: (format) =>
        `runagent-client.${format === 'es' ? 'js' : format}`,
      formats: ['es', 'cjs'],
    },

    rollupOptions: {
      external: [
        'fs',
        'path',
        'crypto',
        'util',
        'events',
        'stream',
        'buffer',
        'url',
        'querystring',
        'http',
        'https',
        'net',
        'tls',
        'zlib',
        'ws',
        'better-sqlite3',
        'os',
      ],

      output: {
        globals: {
          ws: 'WebSocket',
        },
        interop: 'auto',
      },
    },

    target: 'es2020',
    sourcemap: true,
    emptyOutDir: true,
    minify: 'esbuild',
  },

  define: {
    __IS_NODE__: JSON.stringify(
      typeof process !== 'undefined' && process.versions?.node
    ),
    __IS_BROWSER__: JSON.stringify(typeof window !== 'undefined'),
  },
});
