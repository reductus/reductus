#!/usr/bin/env node

import {default as esbuild} from 'esbuild';

esbuild.build({
    entryPoints: ['js/main.js'],
    bundle: true,
    minify: true,
    sourcemap: true,
    outfile: 'dist/js/main.js',
  }).catch(() => process.exit(1))

esbuild.build({
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

  
//esbuild --bundle --minify js/main.js --outfile=dist/js/main.js; 
// esbuild --bundle --minify css/index_prod.css --outfile=dist/css/index.css --loader:.woff=dataurl --loader:.woff2=dataurl --loader:.ttf=dataurl --loader:.eot=dataurl;
