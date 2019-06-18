import {extend} from '../libraries.js';
const instrument = {};
export default instrument;

// define the loader and categorizers for ncnr.sans instrument
function load_tas(load_params, db, noblock, return_type) {
  // load params is a list of:  
  // {datasource: "ncnr", path: "ncnrdata/cgd/...", mtime: 12319123109}
  var noblock = (noblock == true); // defaults to false if not specified
  var return_type = return_type || 'metadata';
  var calc_params = load_params.map(function(lp) {
    return {
      template: {
        "name": "loader_template",
        "description": "TAS remote loader",
        "modules": [
          {"module": "ncnr.tas.LoadTAS", "version": "0.1", "config": {}}
        ],
        "wires": [],
        "instrument": "ncnr.tas",
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

var TAS_REGEXP = /\.(bt4|bt7|ng5)$/
instrument.files_filter = function(x) { return (TAS_REGEXP.test(x) && (/^(fp|fm)/.test(x) == false) ) };
instrument.load_file = load_tas;
instrument.default_categories = [
  [["filename"]]
];
instrument.categories = extend(true, [], instrument.default_categories);

instrument.decorators = [];