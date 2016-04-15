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
    return webreduce.server_api.calc_terminal(template, config, module_id, terminal_id, "metadata").then(function(result) {
      result.values.forEach(function(v) {v.mtime = mtime});
      if (db) { db[path] = result.values; }
      return result.values
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
  
  var primary_axis = {
    "specular": "Qz_target",
    "background+": "Qz_target",
    "background-": "Qz_target",
    "slit": "Qz_target",
    "intensity": "Qz_target", // what slit scans are called in refldata
    "rock qx": "Qx_target", // curve with fixed Qz
    "rock sample": "sample/angle_x", // Rocking curve with fixed detector angle
    "rock detector": "detector/angle_x" //Rocking curve with fixed sample angle
  }
  
  var get_refl_item = function(obj, path) {
    var result = obj,
        keylist = path.split("/");
    while (keylist.length > 0) {
      result = result[keylist.splice(0,1)];
    }
    return result;
  }
  
  function plot(ospec_objs) {
    // entry_ids is list of {path: path, filename: filename, entryname: entryname} ids
    var series = new Array();
    var datas = [], xcol;
    var ycol = "v", ylabel = "y-axis", dycol = "dv";
    var xcol = "x", xlabel = "x-axis", dxcol = "dx";
    refl_objs.forEach(function(entry) {
      var intent = entry['intent'];
      var ydata = get_refl_item(entry, ycol);
      var dydata = get_refl_item(entry, dycol);
      var xdata = get_refl_item(entry, xcol);
      ylabel = get_refl_item(entry, "vlabel");
      ylabel += "(" + get_refl_item(entry, "vunits") + ")";
      xlabel = get_refl_item(entry, "xlabel");
      xlabel += "(" + get_refl_item(entry, "xunits") + ")";
      var xydata = [], x, y, dy, ynorm;
      for (var i=0; i<xdata.length || i<ydata.length; i++) {
        x = (i<xdata.length) ? xdata[i] : x; // use last value
        y = (i<ydata.length) ? ydata[i] : y; // use last value
        dy = (i<dydata.length) ? dydata[i] : dy; // use last value
        xydata[i] = [x,y,{yupper: y+dy, ylower:y-dy,xupper:x,xlower:x}];
      }
      datas.push(xydata);
      series.push({label: entry.name + ":" + entry.entry});

    });
    var plottable = {
      type: "1d",
      series: series,
      axes: {xaxis: {label: xlabel}, yaxis: {label: ylabel}},
      data: datas
    }

    return plottable
  } 
  
  instrument.plot = function(objs) { 
    return objs.slice(-1)[0].plottable[0];
  };
  instrument.load_file = load_ospec; 
  instrument.categorizers = [
    function(info) { return info.friendly_name },
    function(info) { return info.path }
  ];
  
  
  instrument.decorators = [];
    
})(webreduce.instruments['ncnr.ospec']);

