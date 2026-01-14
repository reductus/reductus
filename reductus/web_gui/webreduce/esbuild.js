#!/usr/bin/env node

import esbuild from 'esbuild';
import fs from 'fs';
import path from 'path';
import { copyRecursiveSync } from './copy_recursive_sync.mjs';

const __dirname = path.resolve();

await esbuild.build({
  entryPoints: ['js/main.js'],
  bundle: true,
  minify: true,
  sourcemap: true,
  outdir: 'dist/js',
  target: 'es2016',
  alias: {
    // Use Vue's full build with template compiler instead of runtime-only
    'vue': 'vue/dist/vue.esm-bundler.js'
  },
  plugins: [
  ],
}).catch(() => process.exit(1))

await esbuild.build({
  entryPoints: ['css/index_prod.css'],
  bundle: true,
  minify: true,
  loader: {
    ".woff": "dataurl",
    ".woff2": "dataurl",
    ".ttf": "dataurl",
    ".eot": "dataurl"
  },
  outfile: 'dist/css/index.css',
}).catch(() => process.exit(1))

let mode = fs.constants.COPYFILE_FICLONE;

copyRecursiveSync('index.html', 'dist/index.html', mode);
copyRecursiveSync('favicon.ico', 'dist/favicon.ico', mode);
copyRecursiveSync('img', 'dist/img', mode);
