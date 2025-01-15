import {extend} from '../libraries.js';
import { add_viewer_link, add_sample_description } from './decorators.js';
const instrument = {};
export default instrument;

// define the loader and categorizers for xrr instrument
function load_refl(load_params, db, noblock, return_type) {
  // load params is a list of: 
  // {datasource: "ncnr", path: "ncnrdata/cgd/...", mtime: 12319123109}
  var noblock = (noblock == true); // defaults to false if not specified
  var return_type = return_type || 'metadata';
  var calc_params = load_params.map(function(lp) {
    return {
      template: {
        "name": "loader_template",
        "description": "ReflData remote loader",
        "modules": [
          {"module": "xrr.ncnr_load", "version": "0.1", "config": {}}
        ],
        "wires": [],
        "instrument": "ncnr.magik",
        "version": "0.0"
      }, 
      config: {"0": {"filelist": [{"path": lp.path, "source": lp.source, "mtime": lp.mtime}]}},
      node: 0,
      terminal:  "output",
      return_type: return_type
    }
  });
  return calc_params;
}

function make_range_icon(global_min_x, global_max_x, min_x, max_x) {
  var icon_width = 75;
  var rel_width = Math.abs((max_x - min_x) / (global_max_x - global_min_x));
  var width = icon_width * rel_width;
  var rel_x = Math.abs((min_x - global_min_x) / (global_max_x - global_min_x));
  var x = icon_width * rel_x;
    
  var output = "<svg class=\"range\" width=\"" + (icon_width + 2) + "\" height=\"12\">";
  output += "<rect width=\"" + width + "\" height=\"10\" x=\"" + x + "\" style=\"fill:IndianRed;stroke:none\"/>"
  output += "<rect width=\"" + icon_width + "\" height=\"10\" style=\"fill:none;stroke:black;stroke-width:1\"/>"
  output += "</svg>"
  return output
}


var get_refl_item = function(obj, path) {
  var result = obj,
      keylist = path.split("/");
  console.log(result, keylist);
  while (keylist.length > 0) {
    result = result[keylist.splice(0,1)];
    console.log(result);
  }
  return result;
}

instrument.load_file = load_refl; 
instrument.default_categories = [
  [["name"]], 
];
instrument.categories = extend(true, [], instrument.default_categories);

function add_range_indicators(node_list, leaf_list, node_parents, file_objs) {
  var propagate_up_levels = 2; // levels to push up xmin and xmax.
  
  // first set min and max for entries:
  for (let leaf of leaf_list) {
    let fileinfo = leaf.metadata.fileinfo;
    var filename = fileinfo.filename;
    var file_obj = file_objs[filename];
    var entry = file_obj.values.filter(function(f) {return f.entry == fileinfo.entryname});
    if (entry && entry[0]) {
      var e = entry[0];
      var xaxis = 'x'; // primary_axis[e.intent || 'specular'];
      if (!(get_refl_item(entry[0], xaxis))) { console.log(entry[0]); throw "error: no such axis " + xaxis + " in entry for intent " + e.intent }
      var extent = get_extent(get_refl_item(entry[0], xaxis));
      console.log(leaf, extent);
      leaf.metadata.range = extent;
      let node_id = leaf.id;
      for (var i=0; i<propagate_up_levels; i++) {
        var parent = node_parents[node_id];
        if (!parent) { break }

        parent.metadata = parent.metadata || {};
        if (parent.metadata.range != null) {
          parent.metadata.range = [
            Math.min(extent[0], parent.metadata.range[0]),
            Math.max(extent[1], parent.metadata.range[1])
          ]
        }
        else {
          parent.metadata.range = extent;
        }
        node_id = parent.id;
      }
    }
  }

  // then go back through add range indicators
  for (let node of node_list) {
    let parent = node_parents[node.id];
    if (!parent) {continue}
    var l = (node.metadata || {}).range;
    var p = (parent.metadata || {}).range;
    if (l != null && p != null) {
      var range_icon = make_range_icon(parseFloat(p[0]), parseFloat(p[1]), parseFloat(l[0]), parseFloat(l[1]));
      (node.metadata.right_decorators = node.metadata.right_decorators || []).push(range_icon);
      node.text += range_icon;
    }
  }
}

instrument.decorators = [add_range_indicators, add_viewer_link, add_sample_description];
instrument.export_targets = [
  { 
    "id": "unpolarized_reflcalc",
    "label": "webfit",
    "type": "webapi",
    "url": "https://ncnr.nist.gov/instruments/magik/calculators/reflectivity-calculator.html",
    "method": "set_data"
  }
]

const BRUKER_REGEXP = /\.raw$/
const RIGAKU_REGEXP = /\.ras$/
const XRDML_REGEXP = /\.xrdml$/

instrument.files_filter = function(x) {
  return (
    BRUKER_REGEXP.test(x) ||
    RIGAKU_REGEXP.test(x) ||
    XRDML_REGEXP.test(x)
  )
}

function get_extent(arr) {
  let len = arr.length;
  let max = -Infinity;
  let min = +Infinity;

  while (len--) {
    max = arr[len] > max ? arr[len] : max;
    min = arr[len] < min ? arr[len] : min;
  }
  return [min, max];
}
  

