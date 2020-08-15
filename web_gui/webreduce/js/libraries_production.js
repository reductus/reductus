import { zip, Inflater, Deflater } from '../node_modules/zip.js/WebContent/index.js';
zip.Inflater = Inflater;
zip.Deflater = Deflater;
export { zip };

export { default as Tree } from '@widgetjs/tree/src/index.js';
import { default as Vue } from 'vue';
import { default as VueMaterial } from 'vue-material';
Vue.use(VueMaterial);
export { Vue };
export { default as vuedraggable } from 'vuedraggable';

// import * as d3 from 'd3/dist/d3.min.js';
export { d3 } from './d3-custom.js';
import * as messagepack from 'messagepack';
export { messagepack };
import PouchDB from 'pouchdb-browser';
export { PouchDB };
export {
  xyChart,
  heatChart,
  heatChartMultiMasked,
  colormap_names,
  get_colormap,
  dataflowEditor,
  extend,
  rectangleSelect,
  xSliceInteractor,
  ySliceInteractor,
  rectangleInteractor,
  ellipseInteractor,
  angleSliceInteractor,
  monotonicFunctionInteractor,
  scaleInteractor,
  rectangleSelectPoints
} from 'd3-science';
//}  from './node_modules/d3-science/src/index.js';
export { default as Split } from 'split.js';
export { default as sha1 } from 'sha1'
export const template_editor_url = "template_editor_live.html";
