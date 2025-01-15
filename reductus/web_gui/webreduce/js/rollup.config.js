import builtins from 'rollup-plugin-node-builtins';
import globals from 'rollup-plugin-node-globals';
import resolve from 'rollup-plugin-node-resolve';
import commonjs from "rollup-plugin-commonjs";
import postcss from 'rollup-plugin-postcss';

export default {
  input: 'main.js',
  output: {
    file: 'bundle.js',
    format: 'iife',
    name: 'webreduce'
  },
  plugins: [
    postcss({
      extensions: [ '.css' ],
      extract: true
    }),
    commonjs({
      ignoreGlobal: true,
    }),
    globals(),
    builtins(),
    resolve()
  ]
};
