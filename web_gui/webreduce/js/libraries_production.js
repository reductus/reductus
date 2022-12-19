import * as zip from '@zip.js/zip.js/lib/zip-full.js';
export { zip };
window.zip = zip;

export { default as Tree } from '@widgetjs/tree/src/index.js';
import Vue from 'vue/dist/vue.esm.js';
import * as vm from 'vue-material/dist/components/index.js';
Vue.use(vm.MdToolbar);
Vue.use(vm.MdSubheader);
Vue.use(vm.MdButton);
Vue.use(vm.MdContent);
Vue.use(vm.MdTabs);
Vue.use(vm.MdMenu);
Vue.use(vm.MdApp);
Vue.use(vm.MdDialog);
Vue.use(vm.MdCheckbox);
Vue.use(vm.MdSnackbar);
Vue.use(vm.MdList);
Vue.use(vm.MdDrawer);
Vue.use(vm.MdIcon);
Vue.use(vm.MdField);
Vue.use(vm.MdProgress);
Vue.use(vm.MdSteppers);
Vue.use(vm.MdDivider);
Vue.use(vm.MdRadio);
window.Vue = Vue;
export { Vue };
export { default as vuedraggable } from 'vuedraggable/src/vuedraggable.js';

// import * as d3 from 'd3/dist/d3.min.js';
export { d3 } from './d3-custom.js';
import * as messagepack from 'messagepack/dist/messagepack.es';
export { messagepack };
import * as idb from 'idb/build/index.js';
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
} from 'd3-science/src/index.js';
//}  from './node_modules/d3-science/src/index.js';
export { default as sha1 } from 'sha1/sha1.js';
export { load as yaml_load } from 'js-yaml';
export { default as Split } from 'split.js/dist/split.es';
export { default as PromiseWorker } from 'promise-worker';
