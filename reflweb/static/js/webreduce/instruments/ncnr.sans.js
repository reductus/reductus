// requires(webreduce.server_api)
webreduce = window.webreduce || {};
webreduce.instruments = webreduce.instruments || {};
webreduce.instruments['ncnr.sans'] = webreduce.instruments['ncnr.sans'] || {};

// define the loader and categorizers for ncnr.sans instrument
(function(instrument) {
  function load_sans(datasource, path, mtime, db){
    var template = {
      "name": "loader_template",
      "description": "SANS remote loader",
      "modules": [
        {"module": "ncnr.sans.LoadSANS", "version": "0.1", "config": {}}
      ],
      "wires": [],
      "instrument": "ncnr.sans",
      "version": "0.0"
    }
    var config = {"0": {"filelist": [{"path": path, "source": datasource, "mtime": mtime, "entries": ["entry"]}]}},
        module_id = 0,
        terminal_id = "output";
    return webreduce.server_api.calc_terminal(template, config, module_id, terminal_id, "metadata").then(function(result) {
      result.values.forEach(function(v) {v.mtime = mtime});
      if (db) { db[path] = result; }
      return result
    })
  }
  
  
  
  instrument.plot = function(result) { 
    var plottable;
    if (result == null) {
      return
    }
    else if (result.datatype == 'ncnr.sans.sans2d' && result.values.length > 0) {
      plottable = result.values.slice(-1)[0].plottable;
    }
    return plottable
  };
  
  instrument.load_file = load_sans;
  instrument.categorizers = [
    function(info) { return info['sample.name'] },
    function(info) { return info['analysis.filepurpose'] },
    function(info) { return info['analysis.intent'] },
    function(info) { return info['run.filename'] }
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
  
  instrument.decorators = [add_sample_description];
    
})(webreduce.instruments['ncnr.sans']);

