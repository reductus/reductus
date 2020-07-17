import {extend} from '../libraries.js';
const instrument = {};
export default instrument;

// define the loader and categorizers for ncnr.refl instrument
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
          {"module": "ncnr.refl.ncnr_load", "version": "0.1", "config": {}}
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
  while (keylist.length > 0) {
    result = result[keylist.splice(0,1)];
  }
  return result;
}

instrument.load_file = load_refl; 
instrument.default_categories = [
  [["sample", "name"]],
  [["intent"]], 
  [["filenumber"]], 
  [["polarization"]]
];
instrument.categories = extend(true, [], instrument.default_categories);

function add_range_indicators(node_list, leaf_list, node_parents, file_objs) {
  var propagate_up_levels = 2; // levels to push up xmin and xmax.
  
  // first set min and max for entries:
  for (let leaf of leaf_list) {
    let fileinfo = leaf.attributes.fileinfo;
    var filename = fileinfo.filename;
    var file_obj = file_objs[filename];
    var entry = file_obj.values.filter(function(f) {return f.entry == fileinfo.entryname});
    if (entry && entry[0]) {
      var e = entry[0];
      var xaxis = 'x'; // primary_axis[e.intent || 'specular'];
      if (!(get_refl_item(entry[0], xaxis))) { console.log(entry[0]); throw "error: no such axis " + xaxis + " in entry for intent " + e.intent }
      var extent = get_extent(get_refl_item(entry[0], xaxis));
      leaf.attributes.range = extent;
      let node_id = leaf.id;
      for (var i=0; i<propagate_up_levels; i++) {
        var parent = node_parents[node_id];
        if (!parent) { break }

        parent.attributes = parent.attributes || {};
        if (parent.attributes.range != null) {
          parent.attributes.range = [
            Math.min(extent[0], parent.attributes.range[0]),
            Math.max(extent[1], parent.attributes.range[1])
          ]
        }
        else {
          parent.attributes.range = extent;
        }
        node_id = parent.id;
      }
    }
  }

  // then go back through add range indicators
  for (let node of node_list) {
    let parent = node_parents[node.id];
    if (!parent) {continue}
    var l = (node.attributes || {}).range;
    var p = (parent.attributes || {}).range;
    if (l != null && p != null) {
      var range_icon = make_range_icon(parseFloat(p[0]), parseFloat(p[1]), parseFloat(l[0]), parseFloat(l[1]));
      (node.attributes.right_decorators = node.attributes.right_decorators || []).push(range_icon);
      node.text += range_icon;
    }
  }
}

function add_sample_description(target, file_objs) {
  var jstree = target.jstree(true);
  var to_decorate = jstree.get_json("#", {"flat": true})
    .filter(function(leaf) { 
      return (leaf.li_attr && 
              'filename' in leaf.li_attr &&
              leaf.li_attr.filename in file_objs &&
              'entryname' in leaf.li_attr && 
              'source' in leaf.li_attr &&
              'mtime' in leaf.li_attr) 
      })
  to_decorate.forEach(function(leaf, i) {
    var values = file_objs[leaf.li_attr.filename].values || [];
    var entry = values.filter(function(f) {return f.entry == leaf.li_attr.entryname});
    if (entry && entry[0]) {
      var e = entry[0];
      if ('sample' in e && 'description' in e.sample) {
        var leaf_actual = jstree._model.data[leaf.id];
        leaf_actual.li_attr.title = e.sample.description;
        var parent_id = leaf.parent;
        var parent = jstree._model.data[parent_id];
        parent.li_attr.title = e.sample.description;
      }
    }
  });
}

function add_viewer_link(node_list, leaf_list, node_parents, file_objs) {
  var parents_decorated = new Set();
  const viewer_link = {
    "ncnr": "https://ncnr.nist.gov/ncnrdata/view/nexus-zip-viewer.html",
    "ncnr_DOI": "https://ncnr.nist.gov/ncnrdata/view/nexus-zip-viewer.html",
    "charlotte": "https://charlotte.ncnr.nist.gov/ncnrdata/view/nexus-zip-viewer.html"
  }

  for (let leaf of leaf_list) {
    let parent = node_parents[leaf.id];
    if (parent && parent.id && !(parents_decorated.has(parent.id))) {
      let fileinfo = leaf.attributes.fileinfo;
      let datasource = fileinfo.source;
      let fullpath = fileinfo.filename;
      if (viewer_link[datasource]) {
        if (datasource == "ncnr_DOI") { fullpath = "ncnrdata" + fullpath; }
        let pathsegments = fullpath.split("/");
        let pathlist = pathsegments.slice(0, pathsegments.length-1).join("+");
        let filename = pathsegments.slice(-1);
        let viewer = viewer_link[datasource];
        let hdf_or_zip = (NEXUS_REGEXP.test(fullpath) ? viewer.replace("-zip-", "-hdf-") : viewer);
        let link = `<a href="${hdf_or_zip}?pathlist=${pathlist}&filename=${filename}" target="_blank" style="text-decoration:none;">&#9432;</a>`;
        
        parent.text += link;
        parents_decorated.add(parent.id);
      }
    }
  }
}

instrument.decorators = [add_range_indicators, add_viewer_link];//, add_sample_description];

instrument.export_targets = [
  { 
    "id": "unpolarized_reflcalc",
    "label": "webfit",
    "type": "webapi",
    "url": "https://ncnr.nist.gov/instruments/magik/calculators/reflectivity-calculator.html",
    "method": "set_data"
  },
  { 
    "id": "polarized_reflcalc",
    "label": "pol. webfit",
    "type": "webapi",
    "url": "https://ncnr.nist.gov/instruments/magik/calculators/magnetic-reflectivity-calculator.html",
    "method": "set_data"
  }
]

var NEXUZ_REGEXP = /\.nxz\.[^\.\/]+$/
var NEXUS_REGEXP = /\.nxs\.[^\.\/]+(\.zip)?$/
var BRUKER_REGEXP = /\.ra[ws]$/

instrument.files_filter = function(x) {
  return (
    BRUKER_REGEXP.test(x) ||
    ((NEXUZ_REGEXP.test(x) || NEXUS_REGEXP.test(x))&&
        (/^(fp_)/.test(x) == false) &&
        (/^rapidscan/.test(x) == false) &&
        (/^scripted_findpeak/.test(x) == false))
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
  

