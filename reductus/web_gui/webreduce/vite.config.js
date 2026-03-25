import { defineConfig } from 'vite';
// import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  // Use the index.html in this directory as the entry point
  root: '.',
  base: './',
  resolve: {
    alias: {
      server_api: path.resolve(__dirname, './js/server_api/api_msgpack.js'),
      vue: 'vue/dist/vue.esm-bundler.js', // Use the full build of Vue with template compiler
    },
  },
  plugins: [
    // Vue is loaded via CDN in index.html, but the plugin is kept for potential .vue files.
    // vue({}),
  ],
  build: {
    outDir: 'dist',
    assetsDir: '', // place assets (favicon, images) at the root of dist
    rollupOptions: {
      input: './index.html',
      // Preserve the directory structure for generated JS and CSS
      output: {
        entryFileNames: 'js/[name].[hash].js',
        chunkFileNames: 'js/[name].[hash].js',
        assetFileNames: ({ name }) => {
          if (name && name.endsWith('.css')) {
            return 'css/[name].[hash][extname]';
          }
          // Keep other assets (e.g., favicon.ico, images) at the root level
          return '[name][extname]';
        },
      },
    },
    // Enable source maps for debugging, similar to the esbuild script
    sourcemap: true,
    // Minify the output for production (esbuild does this by default)
    minify: 'esbuild',
    target: 'es2020',
  },
  // Vite automatically copies static files referenced in index.html (favicon, img folder).
});