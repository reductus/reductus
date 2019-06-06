import builtins from 'rollup-plugin-node-builtins';
import globals from 'rollup-plugin-node-globals';
import resolve from 'rollup-plugin-node-resolve';

export default {
  external: ['jquery'],
  input: 'main.js',
  output: {
    file: 'bundle.js',
    format: 'esm',
    globals: {
      jquery: '$',
      d3: 'd3'
    }
  },
  plugins: [
    globals(),
    builtins(),
    resolve({ jsnext: true })
  ]
};
