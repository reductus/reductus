import builtins from 'rollup-plugin-node-builtins';
import globals from 'rollup-plugin-node-globals';
import resolve from 'rollup-plugin-node-resolve';
import commonjs from "rollup-plugin-commonjs";

export default {
  external: ['jquery'],
  input: 'main.js',
  output: {
    file: 'bundle.js',
    format: 'esm',
    globals: {
      jquery: '$'
    }
  },
  plugins: [
    commonjs({
      ignoreGlobal: true,
    }),
    globals(),
    builtins(),
    resolve()
  ]
};
