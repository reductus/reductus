// side-effects... no esm for these yet
//import 'https://www.unpkg.com/jquery-ui@1.12.1/ui/core.js';
import 'https://code.jquery.com/jquery-1.12.4.min.js';
import 'https://code.jquery.com/ui/1.12.1/jquery-ui.min.js';
import 'https://cdn.jsdelivr.net/gh/vakata/jstree@3.3/dist/jstree.min.js';

import 'https://cdn.jsdelivr.net/gh/gildas-lormeau/zip.js@master/WebContent/zip.js';
import 'https://cdn.jsdelivr.net/gh/gildas-lormeau/zip.js@master/WebContent/deflate.js';
import 'https://cdn.jsdelivr.net/gh/gildas-lormeau/zip.js@master/WebContent/inflate.js';
import 'https://cdn.jsdelivr.net/gh/gildas-lormeau/zip.js@master/WebContent/z-worker.js';


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
import {default as _jstree} from "https://dev.jspm.io/npm:jstree@3.3";
import {default as jquery} from "https://dev.jspm.io/npm:jquery@latest";
export {jquery};
export {default as Split} from "https://dev.jspm.io/split.js@1.5.11";
export {default as sha1} from "https://dev.jspm.io/sha1@1.1.1";
export const template_editor_url = "template_editor_live.html";

