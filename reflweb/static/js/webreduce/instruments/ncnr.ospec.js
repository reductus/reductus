// requires(webreduce.server_api)
webreduce = window.webreduce || {};
webreduce.instruments = webreduce.instruments || {};
webreduce.instruments['ncnr.ospec'] = webreduce.instruments['ncnr.ospec'] || {};

// define the loader and categorizers for ncnr.refl instrument
(function(instrument) {
  function load_ospec(load_params, db, noblock) {
    // load params is a list of: 
    // {datasource: "ncnr", path: "ncnrdata/cgd/...", mtime: 12319123109}
    var noblock = noblock != false;
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
        return_type: "metadata"
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
    });
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
      //plottable = result.values.slice(-1)[0].plottable[0];
      plottable = {
        "type": "2d", 
        "datas": result.values.map(function(v) { return v.plottable[0] })
      }
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
  
  function add_viewer_link(target) {
    var jstree = target.jstree(true);
    var source_id = target.parent().attr("id");
    var path = webreduce.getCurrentPath(target.parent());
    var leaf, first_child, entry;
    for (fn in jstree._model.data) {
      leaf = jstree._model.data[fn];
      if (leaf.children.length > 0) {
        first_child = jstree._model.data[leaf.children[0]];
        if (first_child.li_attr && 'filename' in first_child.li_attr && 'entryname' in first_child.li_attr && 'source' in first_child.li_attr) {
          var fullpath = first_child.li_attr.filename;
          var datasource = first_child.li_attr.source;
          if (["ncnr", "ncnr_DOI"].indexOf(datasource) < 0) { continue }
          if (datasource == "ncnr_DOI") { fullpath = "ncnrdata" + fullpath; }
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
  }
  
  instrument.decorators = [add_viewer_link];
    
})(webreduce.instruments['ncnr.ospec']);

