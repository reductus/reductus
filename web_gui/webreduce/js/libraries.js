// side-effects... no esm for these yet
import 'https://www.unpkg.com/jquery@2.2.4/dist/jquery.min.js';
import 'https://www.unpkg.com/jstree@3.3.10/dist/jstree.min.js';
import 'https://www.unpkg.com/jquery-ui-dist@1.12.1/jquery-ui.min.js';
let jquery = window.jQuery;
export {jquery};

import {zip, Inflater, Deflater} from 'https://cdn.jsdelivr.net/gh/bmaranville/zip.js@0.0.3/WebContent/index.js';
zip.Inflater = Inflater;
zip.Deflater = Deflater;
export {zip};

//export {default as Tree} from 'https://cdn.jsdelivr.net/gh/bmaranville/treejs@latest/src/index.js';
export {default as Tree} from './treejs/src/index.js';

export { default as Vue } from 'https://cdn.jsdelivr.net/npm/vue@2.6.11/dist/vue.esm.browser.js';
import { default as d3 } from "https://dev.jspm.io/d3@5";
export { d3 };
import { default as messagepack } from "https://dev.jspm.io/npm:messagepack@1.1";
export { messagepack };
import { default as PouchDB } from "https://dev.jspm.io/npm:pouchdb-browser@7";
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
    monotonicFunctionInteractor 
}  from 'https://cdn.jsdelivr.net/gh/usnistgov/d3-science@0.2.2/src/index.js';
//import jquery from "./import_jquery_dev.js";
//import 'https://www.unpkg.com/jstree@3.3.10/dist/jstree.min.js';
//import {default as _jstree} from "https://dev.jspm.io/npm:jstree@3.3/dist/jstree.js";
//import {default as _ui} from "https://dev.jspm.io/npm:jquery-ui-dist@1.12.1/jquery-ui.js";
//export {jquery};
export {default as Split} from "https://dev.jspm.io/split.js@1.5.11";
export {default as sha1} from "https://dev.jspm.io/sha1@1.1.1";
export const template_editor_url = "template_editor_live_dev.html";

