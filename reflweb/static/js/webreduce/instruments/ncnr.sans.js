// requires(webreduce.server_api)
webreduce = window.webreduce || {};
webreduce.instruments = webreduce.instruments || {};
webreduce.instruments['ncnr.sans'] = webreduce.instruments['ncnr.sans'] || {};

// define the loader and categorizers for ncnr.sans instrument
(function(instrument) {
  function load_sans(load_params, db) {
    // load params is a list of: 
    // {datasource: "ncnr", path: "ncnrdata/cgd/...", mtime: 12319123109}
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
        config: {"0": {"filelist": [{"path": lp.path, "source": lp.datasource, "mtime": lp.mtime}]}},
        node: 0,
        terminal:  "output",
        return_type: "metadata"
      }
    });
    return webreduce.editor.calculate(calc_params, false, false).then(function(results) {
      return results.map(function(result, i) {
        var lp = load_params[i];
        if (result && result.values) {
          result.values.forEach(function(v) {v.mtime = lp.mtime});
          if (db) { db[lp.path] = result; }
          return result.values;
        }
      })
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
      var name = entry.metadata['run.filePrefix'] + entry.metadata['run.experimentScanID'];
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
        "datas": result.values.map(function(v) { return v.plottable })
      }
    }
    else if (result.datatype == 'ncnr.sans.params' && result.values.length > 0) {
      plottable = {"type": "params", "params": result.values}
    }
    return plottable
  };
  
  instrument.load_file = load_sans;
  instrument.categorizers = [
    function(info) { return (info['analysis.groupid']) },
    function(info) { return info['analysis.intent'] },
    function(info) { return info['run.configuration'] },
    //function(info) { return info['analysis.filepurpose'] },
    //function(info) { return info['run.filename'] }
    //*****************************************************************
    //  Using filename is probably a good idea, long term... 
    //  this is a temporary measure for identifying VAX files by name:
    //*****************************************************************
    //function(info) { return (info['run.filePrefix'] + info['run.experimentScanID']) }
    function(info) { return (info['run.experimentScanID'] + ':' + info['sample.description']) }
  ];
  
  function add_sample_description(target) {
    var jstree = target.jstree(true);
    var source_id = target.parent().attr("id");
    var path = webreduce.getCurrentPath(target.parent());
    var file_objs = webreduce.editor._file_objs[path];
    var leaf, entry;
    for (fn in jstree._model.data) {
      leaf = jstree._model.data[fn];
      if (leaf.li_attr && 'filename' in leaf.li_attr && 'entryname' in leaf.li_attr) {
        entry = file_objs[leaf.li_attr.filename].values.filter(function(f) {return f.entry == leaf.li_attr.entryname});
        if (entry && entry[0]) {
          var e = entry[0];
          //console.log(e);
          if ('sample.description' in e) {
            leaf.li_attr.title = e['sample.description'];
            var parent_id = leaf.parent;
            parent = jstree._model.data[parent_id];
            parent.li_attr.title = e['sample.description'];
          }
        }
      }
    }
  }
  
  function add_counts(target) {
    var jstree = target.jstree(true);
    var source_id = target.parent().attr("id");
    var path = webreduce.getCurrentPath(target.parent());
    var file_objs = webreduce.editor._file_objs[path];
    var leaf, entry;
    for (fn in jstree._model.data) {
      leaf = jstree._model.data[fn];
      if (leaf.li_attr && 'filename' in leaf.li_attr && 'entryname' in leaf.li_attr && 'datasource' in leaf.li_attr) {
        var file_objs = webreduce.editor._file_objs[leaf.li_attr.datasource][path];
        entry = file_objs[leaf.li_attr.filename].values.filter(function(f) {return f.entry == leaf.li_attr.entryname});
        if (entry && entry[0]) {
          var e = entry[0];
          //console.log(e, ('run.detcnt' in e && 'run.moncnt' in e && 'run.rtime' in e));
          if ('run.detcnt' in e && 'run.moncnt' in e && 'run.rtime' in e) {
            leaf.li_attr.title = 't:' + e['run.rtime'] + ' det:' + e['run.detcnt'] + ' mon:' + e['run.moncnt'];
            //var parent_id = leaf.parent;
            //parent = jstree._model.data[parent_id];
            //parent.li_attr.title = e['sample.description'];
          }
        }
      }
    }
  }
  
  function add_viewer_link(target) {
    var jstree = target.jstree(true);
    var source_id = target.parent().attr("id");
    var path = webreduce.getCurrentPath(target.parent());
    var file_objs = webreduce.editor._file_objs[path];
    var leaf, first_child, entry;
    for (fn in jstree._model.data) {
      leaf = jstree._model.data[fn];
      if (leaf.li_attr && 'filename' in leaf.li_attr && 'entryname' in leaf.li_attr) {
        var fullpath = leaf.li_attr.filename;
        var pathsegments = fullpath.split("/");
        var pathlist = pathsegments.slice(0, pathsegments.length-1).join("+");
        var filename = pathsegments.slice(-1);
        var link = "<a href=\"http://ncnr.nist.gov/ipeek/nexus-zip-viewer.html";
        link += "?pathlist=" + pathlist;
        link += "&filename=" + filename;
        link += "\" style=\"text-decoration:none;\">&#9432;</a>";
        leaf.text += link;
      }
    }
  }
  
  instrument.decorators = [add_viewer_link, add_counts];
    
})(webreduce.instruments['ncnr.sans']);

