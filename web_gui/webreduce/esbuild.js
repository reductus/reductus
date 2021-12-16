#!/usr/bin/env node

import esbuild from 'esbuild';
import alias from 'esbuild-plugin-alias';
import fs from 'fs';
import path from 'path';

const __dirname = path.resolve();

// This function adapted from https://stackoverflow.com/a/22185855
// with license https://creativecommons.org/licenses/by-sa/4.0/
/**
 * Look ma, it's cp -R.
 * @param {string} src  The path to the thing to copy.
 * @param {string} dest The path to the new copy.
 */
var copyRecursiveSync = function(src, dest, mode) {
  var exists = fs.existsSync(src);
  var stats = exists && fs.statSync(src);
  var isDirectory = exists && stats.isDirectory();
  if (isDirectory) {
    if (!fs.existsSync(dest)) {
        fs.mkdirSync(dest);
    }
    fs.readdirSync(src).forEach(function(childItemName) {
      copyRecursiveSync(path.join(src, childItemName),
                        path.join(dest, childItemName), mode);
    });
  } else {
    fs.copyFileSync(src, dest, mode);
  }
};

await esbuild.build({
    entryPoints: ['js/main.js'],
    bundle: true,
    minify: true,
    sourcemap: true,
    outdir: 'dist/js',
    target: 'es2016',
    plugins: [
        alias({
            './libraries.js': path.resolve(__dirname, `js/libraries_production.js`),
            '../libraries.js': path.resolve(__dirname, `js/libraries_production.js`),
            '../../libraries.js': path.resolve(__dirname, `js/libraries_production.js`)
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
    outfile: 'dist/css/index.css',
  }).catch(() => process.exit(1))

let mode = fs.constants.COPYFILE_FICLONE;
copyRecursiveSync('index.html', 'dist/index.html', mode);
copyRecursiveSync('favicon.ico', 'dist/favicon.ico', mode);
copyRecursiveSync('img', 'dist/img', mode);
