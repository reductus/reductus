// requires(webreduce.server_api)
webreduce = window.webreduce || {};
webreduce.instruments = webreduce.instruments || {};
webreduce.instruments['ncnr.ospec'] = webreduce.instruments['ncnr.ospec'] || {};

// define the loader and categorizers for ncnr.refl instrument
(function(instrument) {
  function load_ospec(datasource, path, mtime, db){
    var template = {
      "name": "loader_template",
      "description": "Offspecular remote loader",
      "modules": [
        {"module": "ncnr.ospec.LoadMAGIKPSD", "version": "0.1", "config": {}}
      ],
      "wires": [],
      "instrument": "ncnr.magik",
      "version": "0.0"
    }
    var config = {"0": {"fileinfo": {"path": path, "source": datasource, "mtime": mtime}}},
        module_id = 0,
        terminal_id = "output";
    return webreduce.editor.calculate(template, config, module_id, terminal_id, "metadata", false).then(function(result) {
      result.values.forEach(function(v) {v.mtime = mtime});
      if (db) { db[path] = result; }
      return result
    })
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
  
  instrument.plot = function(result) { 
    var plottable;
    if (result == null) {
      return
    }
    else if (result.datatype == 'ncnr.ospec.ospec2d' && result.values.length > 0) {
      plottable = result.values.slice(-1)[0].plottable[0];
    }
    else if (result.datatype == 'ncnr.ospec.ospec1d' && result.values.length > 0) {
      plottable = result.values.slice(-1)[0].plottable[0];
    }
    else if (result.datatype == 'ncnr.ospec.params') {
      plottable = {"type": "params", "params": result.values}
    }
    return plottable
  };
  
  instrument.load_file = load_ospec;
  instrument.categorizers = [
    function(info) { return info.friendly_name },
    function(info) { return info.path }
  ];
  
  
  instrument.decorators = [];
    
})(webreduce.instruments['ncnr.ospec']);

