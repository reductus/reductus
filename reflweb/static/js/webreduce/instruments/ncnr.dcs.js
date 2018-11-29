// requires(webreduce.server_api)
webreduce = window.webreduce || {};
webreduce.instruments = webreduce.instruments || {};
webreduce.instruments['ncnr.dcs'] = webreduce.instruments['ncnr.dcs'] || {};

// define the loader and categorizers for ncnr.sans instrument
(function(instrument) {
  function load_dcs(load_params, db, noblock, return_type) {
    // load params is a list of: 
    // {datasource: "ncnr", path: "ncnrdata/cgd/...", mtime: 12319123109}
    var noblock = (noblock == true); // defaults to false if not specified
    var return_type = return_type || 'metadata';
    var calc_params = load_params.map(function(lp) {
      return {
        template: {
          "name": "loader_template",
          "description": "DCS remote loader",
          "modules": [
            {"module": "ncnr.dcs.LoadDCS", "version": "0.1", "config": {}}
          ],
          "wires": [],
          "instrument": "ncnr.dcs",
          "version": "0.0"
        },
        config: {"0": {"filelist": [{"path": lp.path, "source": lp.source, "mtime": lp.mtime}]}},
        node: 0,
        terminal:  "output",
        return_type: return_type
      }
    });
    return webreduce.editor.calculate(calc_params, false, noblock).then(function(results) {
      results.forEach(function(result, i) {
        var lp = load_params[i];
        if (result && result.values) {
          result.values.forEach(function(v) {v.mtime = lp.mtime});
          if (db) { db[lp.path] = result; }
        }
      });
      return results;
    })
  }

  var DCS_REGEXP = /\.dcs\.gz$/
  instrument.files_filter = function(x) { return (DCS_REGEXP.test(x)) };
  instrument.load_file = load_dcs;
  instrument.default_categories = [
    [["comments"]],
    [["temp_setpoint"], ["field_setpoint"]],
    [["name"]]
  ];
  instrument.categories = jQuery.extend(true, [], instrument.default_categories);  
  
  instrument.decorators = [];
    
})(webreduce.instruments['ncnr.dcs']);

