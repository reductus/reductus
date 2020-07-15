//import * as d3 from "./web_modules/d3.js";
import "../css/index_prod.css";

import jquery from './import_jquery.js';
import "jquery-ui-dist/jquery-ui.js";
import "jstree/dist/jstree.js";
export {jquery};

import {zip, Inflater, Deflater} from '../node_modules/zip.js/WebContent/index.js';
zip.Inflater = Inflater;
zip.Deflater = Deflater;
export {zip};

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
