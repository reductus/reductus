import { defineConfig } from 'vite';
// import vue from '@vitejs/plugin-vue';
import path from 'path';
import fs from 'fs';

const alias = {
  vue: 'vue/dist/vue.esm-bundler.js',
  server_api: path.resolve(__dirname, './js/server_api/api_webworker.js'),
};

const OUTDIR = 'dist_webworker';

export default defineConfig({
  // Use the index.html in this directory as the entry point
  root: '.',
  base: './',
  resolve: {
    alias: alias,
  },
  plugins: [
    // Vue is loaded via CDN in index.html, but the plugin is kept for potential .vue files.
    // vue({}),
    getWheelFilesPlugin(),
  ],
  define: { ENABLE_UPLOADS: 'true' },
  build: {
    outDir: OUTDIR,
    assetsDir: '', // place assets (favicon, images) at the root of dist
    rollupOptions: {
      input: {
        main: './index.html',                    // UI HTML (will pull in js/main.js)
        // worker: './js/server_api/worker.js',     // Web‑worker script
        // css: './css/index_prod.css',             // CSS for the worker UI
      },

      // ----------------------------------------------------------------
      // 8️⃣  Output naming – keep the hash pattern you already use
      output: {
        // entryFileNames applies to the UI entry (`main` → index.html → JS)
        entryFileNames: 'js/[name].[hash].js',
        // chunkFileNames for shared chunks
        chunkFileNames: 'js/[name].[hash].js',
        // assetFileNames for CSS and any other assets
        assetFileNames: ({ name }) => {
          if (name && name.endsWith('.css')) {
            return 'css/[name].[hash][extname]';
          }
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
  worker: {
    format: 'es', // Ensure worker is output as an ES module
    rollupOptions: {
      // Mark the CDN URL as external so Rolldown doesn't try to bundle it
      external: [
        /^https?:\/\/cdn\.jsdelivr\.net\/.*/,
        /^https?:\/\/unpkg\.com\/.*/
      ],
    },
  },
  // Vite automatically copies static files referenced in index.html (favicon, img folder).
});

function writeWheelListPlugin() {
  return {
    name: 'write-wheel-list',
    // `closeBundle` is called once the whole output directory is ready.
    // It receives no args; we can read the directory ourselves.
    closeBundle() {
      // The output folder we use for the worker build
      const outDir = path.resolve(__dirname, OUTDIR);

      // Find every file that ends with `.whl` (the original script looked
      // inside the *same* folder). If you also need to search sub‑folders,
      // use `fs.readdirSync(..., { withFileTypes: true })` and recurse.
      const files = fs
        .readdirSync(outDir)
        .filter((f) => f.endsWith('.whl'));

      // Write the JSON file – this mirrors the old `fs.writeFileSync`
      const jsonPath = path.join(outDir, 'wheel_files.json');
      fs.writeFileSync(jsonPath, JSON.stringify(files, null, 2));

      // Optional: log so you can see it in the console
      console.log(`[vite] wheel_files.json written (${files.length} entries)`);
    },
  };
}

function getWheelFilesPlugin() {
  return {
    name: 'get-wheel-files',
    // `buildStart` is called at the very beginning of the build process.
    // It can return a Promise, so we can read the directory before anything else happens.
    async closeBundle() {
      const srcDir = path.resolve(__dirname, '..', '..', '..', 'dist');

      const outDir = path.resolve(__dirname, OUTDIR);

      if (!fs.existsSync(srcDir)) {
        this.error(`copy-wheel-files: source directory does not exist → ${srcDir}`);
        return;
      }

      // Ensure the destination folder exists.
      fs.mkdirSync(outDir, { recursive: true });

      // Find all *.whl files in the source folder
      const wheelFiles = fs.readdirSync(srcDir).filter(f => f.endsWith('.whl'));

      // Copy each file.
      for (const file of wheelFiles) {
        const srcPath = path.join(srcDir, file);
        const destPath = path.join(outDir, file);
        fs.copyFileSync(srcPath, destPath);
      }

      // Write the JSON file – this mirrors the old `fs.writeFileSync`
      const jsonPath = path.join(outDir, 'wheel_files.json');
      fs.writeFileSync(jsonPath, JSON.stringify(wheelFiles, null, 2));

    }
  };
}