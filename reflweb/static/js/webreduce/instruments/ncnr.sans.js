// requires(webreduce.server_api)
webreduce = window.webreduce || {};
webreduce.instruments = webreduce.instruments || {};
webreduce.instruments['ncnr.sans'] = webreduce.instruments['ncnr.sans'] || {};

// define the loader and categorizers for ncnr.sans instrument
(function(instrument) {
  function load_sans(load_params, db, noblock, return_type) {
    // load params is a list of: 
    // {datasource: "ncnr", path: "ncnrdata/cgd/...", mtime: 12319123109}
    var noblock = (noblock == true); // defaults to false if not specified
    var return_type = return_type || 'metadata';
    var calc_params = load_params.map(function(lp) {
      return {
        template: {
          "name": "loader_template",
          "description": "SANS remote loader",
          "modules": [
            {"module": "ncnr.sans.LoadSANS", "version": "0.1", "config": {}}
          ],
          "wires": [],
          "instrument": "ncnr.sans",
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
  
  function plot_1d(sans1d_objs) {
    // entry_ids is list of {path: path, filename: filename, entryname: entryname} ids
    var series = new Array();
    var datas = [];
    var ylabel = 'y-axis',
        xlabel = 'x-axis';
    sans1d_objs.forEach(function(entry) {
      var ydata = entry.v;
      var dydata = entry.dv.map(Math.sqrt);
      var xdata = entry.x;
      ylabel = entry.vlabel;
      ylabel += "(" + entry.vunits + ")";
      yscale = entry.vscale;
      xlabel = entry.xlabel;
      xlabel += "(" + entry.xunits + ")";
      xscale = entry.xscale;
      var xydata = [], x, y, dy, ynorm;
      for (var i=0; i<xdata.length || i<ydata.length; i++) {
        x = (i<xdata.length) ? xdata[i] : x; // use last value
        y = (i<ydata.length) ? ydata[i] : y; // use last value
        dy = (i<dydata.length) ? dydata[i] : dy; // use last value
        xydata[i] = [x,y,{yupper: y+dy, ylower:y-dy,xupper:x,xlower:x}];
      }
      datas.push(xydata);
      var name = entry.metadata['run.experimentScanID']+': ' + entry.metadata['sample.labl'];
      name += entry.metadata.extra_label || "";
      series.push({label: name});

    });
    var plottable = {
      type: "1d",
      options: {
        series: series,
        axes: {xaxis: {label: xlabel}, yaxis: {label: ylabel}},
        ytransform: yscale,
        xtransform: xscale
      },
      data: datas
    }

    return plottable
  } 
  
  instrument.plot = function(result) { 
    var plottable;
    if (result == null) {
      return
    }
    else if (result.datatype == 'ncnr.sans.sans1d' && result.values.length > 0) {
      plottable = plot_1d(result.values);
    }
    else if (result.datatype == 'ncnr.sans.sans2d' && result.values.length > 0) {
      //plottable = result.values.slice(-1)[0].plottable;
      plottable = {
        "type": "2d", 
        "datas": result.values
      }
    }
    else if (result.datatype == 'ncnr.sans.params' && result.values.length > 0) {
      plottable = {"type": "params", "params": result.values}
    }
    return plottable
  };
  
  instrument.load_file = load_sans;
  instrument.default_categories = [
    [["analysis.groupid"]],
    [["analysis.intent"]], 
    [["run.configuration"]], 
    [["run.experimentScanID"],["sample.description"]]
  ];
  instrument.categories = jQuery.extend(true, [], instrument.default_categories);  
  
  function add_sample_description(target, file_objs) {
    var jstree = target.jstree(true);
    //var path = webreduce.getCurrentPath(target.parent());
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
      var filename = leaf.li_attr.filename;
      var file_obj = file_objs[filename];
      var entry = file_obj.values.filter(function(f) {return f.entry == leaf.li_attr.entryname});
      if (entry && entry[0]) {
        var e = entry[0];
        if ('sample.description' in e) {
          leaf.li_attr.title = e['sample.description'];
          var parent_id = leaf.parent;
          parent = jstree._model.data[parent_id];
          parent.li_attr.title = e['sample.description'];
        }
      }
    });
  }
  
  
  function add_counts(target, file_objs) {
    var jstree = target.jstree(true);
    var leaf, entry;
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
      var filename = leaf.li_attr.filename;
      var file_obj = file_objs[filename];
      var entry = file_obj.values.filter(function(f) {return f.entry == leaf.li_attr.entryname});
      if (entry && entry[0]) {
        var e = entry[0];
        //console.log(e, ('run.detcnt' in e && 'run.moncnt' in e && 'run.rtime' in e));
        if ('run.detcnt' in e && 'run.moncnt' in e && 'run.rtime' in e) {
          var leaf_actual = jstree._model.data[leaf.id];
          leaf_actual.li_attr.title = 't:' + e['run.rtime'] + ' det:' + e['run.detcnt'] + ' mon:' + e['run.moncnt'];
        }
      }
    });
  }
  
  function add_viewer_link(target, file_objs) {
    var jstree = target.jstree(true);
    var to_decorate = jstree.get_json("#", {"flat": true})
      .filter(function(leaf) { 
        return (leaf.li_attr && 
                'filename' in leaf.li_attr && 
                'source' in leaf.li_attr) 
        })
    to_decorate.forEach(function(leaf, i) {
      var fullpath = leaf.li_attr.filename;
      var datasource = leaf.li_attr.source;
      if (["ncnr", "ncnr_DOI"].indexOf(datasource) < 0) { return }
      if (datasource == "ncnr_DOI") { fullpath = "ncnrdata" + fullpath; }
      var pathsegments = fullpath.split("/");
      var pathlist = pathsegments.slice(0, pathsegments.length-1).join("+");
      var filename = pathsegments.slice(-1);
      var link = "<a href=\"http://ncnr.nist.gov/ipeek/nexus-zip-viewer.html";
      link += "?pathlist=" + pathlist;
      link += "&filename=" + filename;
      link += "\" style=\"text-decoration:none;\">&#9432;</a>";
      var leaf_actual = jstree._model.data[leaf.id];
      leaf_actual.text += link;
    })
  }
  
  instrument.decorators = [add_viewer_link, add_counts];
    
})(webreduce.instruments['ncnr.sans']);

