//import * as d3 from "./web_modules/d3.js";
import * as d3 from 'd3';
export {d3};
import * as messagepack from 'messagepack';
export {messagepack};
import PouchDB from 'pouchdb-browser';
export {PouchDB};
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
    monotonicFunctionInteractor 
} from 'd3-science';
//}  from './node_modules/d3-science/src/index.js';
export {default as Split} from 'split.js';
export {default as sha1} from 'sha1'
export const template_editor_url = "template_editor_live_prod.html";
//import {default as _jstree} from 'jstree';
//window.jstree = _jstree
//import './node_modules/jstree/dist/themes/default/style.css';
//import {default as jquery} from 'jquery';
//window.jQuery = jquery;
//import {default as jquery_ui} from 'jquery-ui-dist';
//export {jquery_ui};
//window.jqui = _jquery_ui;
//export {jquery, jquery as jQuery};
