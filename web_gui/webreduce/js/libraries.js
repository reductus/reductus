import { zip, Inflater, Deflater } from '../node_modules/zip.js/WebContent/index.js';
zip.Inflater = Inflater;
zip.Deflater = Deflater;
export { zip };

export { default as Tree } from '@widgetjs/tree/src/index.js';
import Vue from 'vue/dist/vue.esm.js';
import { 
    MdButton, 
    MdContent, 
    MdTabs, 
    MdMenu, 
    MdApp, 
    MdDialog, 
    MdSnackbar, 
    MdList 
} from 'vue-material/dist/components/index.js';
import * as vm from 'vue-material/dist/components/index.js';
Vue.use(MdButton);
Vue.use(MdContent);
Vue.use(MdTabs);
Vue.use(MdMenu);
Vue.use(MdApp);
Vue.use(MdDialog);
Vue.use(MdSnackbar);
Vue.use(MdList);
Vue.use(vm.MdDrawer);
Vue.use(vm.MdIcon);
window.Vue = Vue;
export { Vue };
export { default as vuedraggable } from 'vuedraggable';

// import * as d3 from 'd3/dist/d3.min.js';
export { d3 } from './d3-custom.js';
import * as messagepack from 'messagepack';
export { messagepack };
import * as idb from 'idb';
export { idb };
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
