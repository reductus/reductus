import {extend} from '../libraries.js';
import { add_viewer_link } from './decorators.js';
const instrument = {};
export default instrument;

// define the loader and categorizers for ncnr.refl instrument
function load_ospec(load_params, db, noblock, return_type) {
  // load params is a list of: 
  // {datasource: "ncnr", path: "ncnrdata/cgd/...", mtime: 12319123109}
  var noblock = (noblock == true); // defaults to false if not specified
  var return_type = return_type || 'metadata';
  var calc_params = load_params.map(function(lp) {
    return {
      template: {
        "name": "loader_template",
        "description": "Offspecular remote loader",
        "modules": [
          {"module": "ncnr.ospec.LoadMAGIKPSD", "version": "0.1", "config": {}}
        ],
        "wires": [],
        "instrument": "ncnr.magik",
        "version": "0.0"
      }, 
      config: {"0": {"fileinfo": {"path": lp.path, "source": lp.source, "mtime": lp.mtime}}},
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


var NEXUZ_REGEXP = /\.nxz\.[^\.\/]+$/
var NEXUS_REGEXP = /\.nxs\.[^\.\/]+(\.zip)?$/

instrument.files_filter = function(x) {
  return (
    (NEXUZ_REGEXP.test(x) &&
        (/^(fp_)/.test(x) == false) &&
        (/^rapidscan/.test(x) == false) &&
        (/^scripted_findpeak/.test(x) == false))
  )
}

instrument.load_file = load_ospec;
instrument.default_categories = [
  [["friendly_name"]],
  [["path"]],
  [["polarization"]]
];
instrument.categories = extend(true, [], instrument.default_categories);
instrument.decorators = [add_viewer_link];
