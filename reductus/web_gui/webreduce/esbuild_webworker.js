#!/usr/bin/env node

import esbuild from 'esbuild';
import alias from 'esbuild-plugin-alias';
import fs from 'fs';
import path from 'path';
import { copyRecursiveSync } from './copy_recursive_sync.mjs';

const __dirname = path.resolve();

await esbuild.build({
  entryPoints: ['js/main.js'],
  bundle: true,
  minify: true,
  sourcemap: true,
  define: { ENABLE_UPLOADS: 'true' },
  outdir: 'dist_webworker/js',
  target: 'es2016',
  plugins: [
    alias({
      './libraries.js': path.resolve(__dirname, `js/libraries_production.js`),
      '../libraries.js': path.resolve(__dirname, `js/libraries_production.js`),
      '../../libraries.js': path.resolve(__dirname, `js/libraries_production.js`),
      './server_api/api_msgpack.js': path.resolve(__dirname, 'js/server_api/api_webworker.js')
    }),
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
  outfile: 'dist_webworker/css/index.css',
}).catch(() => process.exit(1))

let mode = fs.constants.COPYFILE_FICLONE;

copyRecursiveSync('index.html', 'dist_webworker/index.html', mode);
copyRecursiveSync('favicon.ico', 'dist_webworker/favicon.ico', mode);
copyRecursiveSync('img', 'dist_webworker/img', mode);
copyRecursiveSync('js/server_api/worker.js', 'dist_webworker/worker.js', mode);
copyRecursiveSync('../../../dist', 'dist_webworker', mode)

// generate a list of files ending in .whl in the dist folder and write to file
let files = fs.readdirSync('dist_webworker').filter(f => f.endsWith('.whl'));
fs.writeFileSync('dist_webworker/wheel_files.json', JSON.stringify(files));