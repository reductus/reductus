// requires(webreduce.server_api)
webreduce = window.webreduce || {};
webreduce.instruments = webreduce.instruments || {};
webreduce.instruments['ncnr.refl'] = webreduce.instruments['ncnr.refl'] || {};

// define the loader and categorizers for ncnr.refl instrument
(function(instrument) {
  function load_refl(path, mtime, db){
    var template = {
      "name": "loader_template",
      "description": "ReflData remote loader",
      "modules": [
        {"module": "ncnr.refl.super_load", "version": "0.1", "config": {}}
      ],
      "wires": [],
      "instrument": "ncnr.magik",
      "version": "0.0"
    }
    var config = {"0": {"filelist": [{"path": path, "mtime": mtime}]}},
        module_id = 0,
        terminal_id = "output";
    return webreduce.server_api.calc_terminal(template, config, module_id, terminal_id).then(function(result) {
      result.values.forEach(function(v) {v.mtime = mtime});
      if (db) { db[path] = result.values; }
      //console.log(result.result);
      if (webreduce.statusline_log) {
        webreduce.statusline_log("loaded: " + path);
      }
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

    
  function plot_files(file_objs, entry_ids) {
    // entry_ids is list of {path: path, filename: filename, entryname: entryname} ids
    var series = new Array();
    var options = {
      series: series,
      legend: {show: true, left: 150},
      axes: {xaxis: {label: "x-axis"}, yaxis: {label: "y-axis"}}
    };
    var datas = [], xcol;
    var ycol = "detector/counts";
    var ynormcol = "monitor/counts";
    entry_ids.forEach(function(eid) {
      var refl = file_objs[eid.file_obj]
      var entry = refl.filter(function(r) {return r.entry == eid.entryname})[0]
      var intent = entry['intent'];
      var new_xcol = primary_axis[intent];
      if (xcol != null && new_xcol != xcol) {
        throw "mismatched x axes in selection: " + xcol.toString() + " and " + new_xcol.toString();
      }
      else {
        xcol = new_xcol;
      }
      var ydata = get_refl_item(entry, ycol);
      var xdata = get_refl_item(entry, xcol);
      var ynormdata = get_refl_item(entry, ynormcol);
      var xydata = [], x, y, ynorm;
      for (var i=0; i<xdata.length || i<ydata.length; i++) {
        x = (i<xdata.length) ? xdata[i] : x; // use last value
        y = (i<ydata.length) ? ydata[i] : y; // use last value
        ynorm = (i<ynormdata.length) ? ynormdata[i] : ynorm; // use last value
        xydata[i] = [x,y/ynorm];
      }
      datas.push(xydata);
      series.push({label: entry.name + ":" + entry.entry});

    });
    ycol = "detector/counts";
    ynormcol = "monitor/counts";

    return {xcol: xcol, ycol: ycol, series: series, data: datas};
  }
  
  function plot(refl_objs) {
    // entry_ids is list of {path: path, filename: filename, entryname: entryname} ids
    var series = new Array();
    var options = {
      series: series,
      legend: {show: true, left: 150},
      axes: {xaxis: {label: "x-axis"}, yaxis: {label: "y-axis"}}
    };
    var datas = [], xcol;
    var ycol = "v", ylabel = "y-axis";
    var xcol = "x", xlabel = "x-axis";
    var ynormcol = "monitor/counts";
    refl_objs.forEach(function(entry) {
      var intent = entry['intent'];
      var ydata = get_refl_item(entry, ycol);
      var xdata = get_refl_item(entry, xcol);
      ylabel = get_refl_item(entry, "vlabel");
      xlabel = get_refl_item(entry, "xlabel");
      var ynormdata = get_refl_item(entry, ynormcol);
      var xydata = [], x, y, ynorm;
      for (var i=0; i<xdata.length || i<ydata.length; i++) {
        x = (i<xdata.length) ? xdata[i] : x; // use last value
        y = (i<ydata.length) ? ydata[i] : y; // use last value
        ynorm = (i<ynormdata.length) ? ynormdata[i] : ynorm; // use last value
        xydata[i] = [x,y/ynorm];
      }
      datas.push(xydata);
      series.push({label: entry.name + ":" + entry.entry});

    });

    return {xcol: xcol, ycol: ycol, ylabel: ylabel, xlabel: xlabel, series: series, data: datas};
  } 
  
  instrument.plot = plot;
  instrument.plot_files = plot_files;
  instrument.load_file = load_refl; 
  instrument.categorizers = [
    function(info) { return info.sample.name },
    function(info) { return info.intent || "unknown" },
    function(info) { return info.name },
    function(info) { return info.polarization || "unpolarized" }
  ];
  
  function add_range_indicators(target) {
    var propagate_up_levels = 2; // levels to push up xmin and xmax.
    var jstree = target.jstree(true);
    var source_id = target.parent().attr("id");
    var file_objs = webreduce.editor._file_objs[source_id];
    var leaf, entry;
    // first set min and max for entries:
    for (fn in jstree._model.data) {
      leaf = jstree._model.data[fn];
      if (leaf.li_attr && 'filename' in leaf.li_attr && 'entryname' in leaf.li_attr) {
        entry = file_objs[leaf.li_attr.filename].filter(function(f) {return f.entry == leaf.li_attr.entryname});
        if (entry && entry[0]) {
          var e = entry[0];
          var xaxis = primary_axis[e.intent || 'specular'];
          var extent = d3.extent(entry[0][xaxis]);
          leaf.li_attr.xmin = extent[0];
          leaf.li_attr.xmax = extent[1];
          var parent = leaf;
          for (var i=0; i<propagate_up_levels; i++) {
            var parent_id = parent.parent;
            parent = jstree._model.data[parent_id];
            if (parent.li_attr.xmin != null) {
              parent.li_attr.xmin = Math.min(extent[0], parent.li_attr.xmin);
            }
            else {
              parent.li_attr.xmin = extent[0];
            }
            if (parent.li_attr.xmax != null) {
              parent.li_attr.xmax = Math.max(extent[1], parent.li_attr.xmax);
            }
            else {
              parent.li_attr.xmax = extent[1];
            }
          }
        }
      }
    }
    for (fn in jstree._model.data) {
      leaf = jstree._model.data[fn];
      if (leaf.parent == null) {continue}
      var l = leaf.li_attr;
      var p = jstree._model.data[leaf.parent].li_attr;
      if (l.xmin != null && l.xmax != null && p.xmin != null && p.xmax != null) {
        var range_icon = make_range_icon(parseFloat(p.xmin), parseFloat(p.xmax), parseFloat(l.xmin), parseFloat(l.xmax));
        leaf.text += range_icon;
      }
    }
  }
  
  instrument.decorators = [add_range_indicators];
    
})(webreduce.instruments['ncnr.refl']);

