export var editor = {};

import { app } from './main.js';
import {server_api} from './server_api/api_msgpack.js';
import {dependencies} from './deps.js';
import {instruments} from './instruments/index.js';
// now a global...
import {zip} from './libraries.js';
import {d3} from './libraries.js';
import {extend, dataflowEditor} from './libraries.js';
import {PouchDB} from './libraries.js';
import {sha1} from './libraries.js';
import {template_editor_url} from './libraries.js';
import {filebrowser} from './filebrowser.js';
//import {make_fieldUI} from './fieldUI.js';
import { fieldUI } from './ui_components/fields_panel.js';
import { plotter  } from './plot.js';
import { vueMenu } from './menu.js';
import { export_dialog } from './ui_components/export_dialog.js';
import { app_header } from './app_header.js';


editor.instruments = instruments;

editor.dispatch = d3.dispatch("accept", "field_update");

editor.guid = function() {
  var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random()*16|0,v=c=='x'?r:r&0x3|0x8;
    return v.toString(16);});
  return uuid;
}

class inMemoryCache {
  constructor() {
    this.storage = new Map();
    this.adapter = 'memory';
  }
  destroy() {
    this.storage = null;
  }
  async get(key) {
    let storage = this.storage;
    return new Promise(function(resolve, reject) {
      if (storage.has(key)) {
        resolve(storage.get(key));
      }
      else {
        reject("key not found: " + String(key));
      }
    });
  }
  put(key, value) {
    return this.storage.set(key, value);
  }
};

editor.make_cache = function() {
  try {
    this._cache = new PouchDB("calculations", {size: 100});
  } catch (e) {
    if (e.name === "SecurityError") {
      var warning = "Could not store website data - falling back to in-memory storage (may cause memory issues.)";
      warning += "Please adjust your privacy level to allow website data storage (unblock cookies?) and reload page.";
      alert(warning);
      this._cache = new inMemoryCache();
    } else {
      throw e;
    }
  }
}
editor.make_cache();

editor.clear_cache = async function() {
  app_header.instance.show_snackbar("clearing cache...", 4000);
  await this._cache.destroy();
  try {
    this.make_cache();
    app_header.instance.show_snackbar("cache cleared", 4000);
  } catch (e) {
    alert(e + "could not destroy cache")
  }
}

editor.create_instance = function(target_id) {
  // create an instance of the dataflow editor in
  // the html element referenced by target_id
  this._instance = new dataflowEditor(null, d3);
  this._target_id = target_id;
  //this._instance.data([{modules:[],wires: []}]);
  var target = d3.select("#" + target_id);
  target.call(this._instance);
  d3.select("body").on("keydown.accept", null);
  d3.select("body").on("keydown.accept", function() {
    var key = d3.event.key;
    if (key.toLowerCase && key.toLowerCase() == "enter") {
      var accept_fn = d3.select("button.accept.config").on("click");
      if (accept_fn) { accept_fn(); }
      return false
    }
  })
  // add decoration filters and patterns for highlighting filled paths
  var defs = this._instance.svg().append("defs");
  var glow_filter = defs.append("filter")
    .attr("id", "glow")
    .attr("filterUnits", "objectBoundingBox")
    .attr("x", "-50%")
    .attr("y", "-50%")
    .attr("width", "200%")
    .attr("height", "200%")
  
  glow_filter.append("feOffset")
      .attr("result", "offOut")
      .attr("in", "SourceGraphic")
      .attr("dx", 0)
      .attr("dy", 0)
      
  glow_filter.append("feColorMatrix")
      .attr("in", "offOut")
      .attr("result", "matrixOut")
      .attr("type", "matrix")
      .attr("values", "0 0 0 0 0 \
                        1 1 1 1 0 \
                        0 0 0 0 0 \
                        0 0 0 1 0")
                        
  glow_filter.append("feGaussianBlur")
      .attr("in", "matrixOut")
      .attr("result", "blurOut")
      .attr("stdDeviation", 10);

  glow_filter.append("feBlend")
      .attr("in", "SourceGraphic")
      .attr("in2", "blurOut")
      .attr("mode", "normal")

  // on wires with data in them:
  // svg.selectAll("path.wire.filled").style("stroke-dasharray", null).style("stroke", "green");
  // svg.selectAll("path.wire.empty").style("stroke-dasharray", "2,2").style("stroke", "red");

  var output_pattern = defs.append("pattern")
    .attr("id", "output_hatch")
    .attr("patternUnits", "userSpaceOnUse")
    .attr("width", 10)
    .attr("height", 10)
    .append("path")
      .attr("d", "M-1,1 l2,-2 M0,10 l10,-10 M9,11 l2,-2")
      .style("stroke", "#88FFFF")
      .style("stroke-opacity", 1)
      .style("stroke-width", 3)
      
  var input_pattern = defs.append("pattern")
    .attr("id", "input_hatch")
    .attr("patternUnits", "userSpaceOnUse")
    .attr("width", 10)
    .attr("height", 10)
    .style("fill-opacity", 1)
    .append("path")
      .attr("d", "M-1,1 l2,-2 M0,10 l10,-10 M9,11 l2,-2")
      .style("stroke", "#88FF88")
      .style("stroke-opacity", 1)
      .style("stroke-width", 3)
}

function module_clicked_multiple() {
  var editor_select = d3.select("#" + editor._target_id);
  var active_template = editor._active_template;
  app.hide_fields();
  var to_compare = [];
  editor_select.selectAll("g.module").each(function(dd, ii) {
    d3.select(this).selectAll("g.selected rect.terminal").each(function(ddd,iii) {
      var tid = d3.select(this).attr("terminal_id");
      to_compare.push({"node": ii, "terminal": tid})
    });
  });
  compare_in_template(to_compare, active_template);
}

editor.advance_to_output = function() {
  let active_template = editor._active_template;
  let editor_select = d3.select("#" + editor._target_id);
  let selected_terminal = editor_select.select("g.module g.selected rect.terminal");
  let i = editor._active_node;
  let active_module = active_template.modules[i];
  let module_def = editor._module_defs[active_module.module];
  if (selected_terminal.empty()) {
    // then it's a loader that's clicked, with no output selected;
    let first_output = module_def.outputs[0].id;
    let selected_title = editor_select.select("g.module g.title.selected");
    let module_elem = d3.select(selected_title.node().parentNode);
    module_elem.selectAll("g.terminals").classed('selected', function(d) { return d.id == first_output });
  }
  else if (!(selected_terminal.classed("output"))) {
    // find the first output and select that one...
    let first_output = module_def.outputs[0].id;
    let module_elem = d3.select(selected_terminal.node().parentNode.parentNode);
    module_elem.selectAll("g.terminals").classed('selected', function(d) { return d.id == first_output });
  }
  module_clicked_single();
}

function module_clicked_single() {
  app.show_fields();
  var active_template = editor._active_template;
  var editor_select = d3.select("#" + editor._target_id);
  var selected_terminal = editor_select.select("g.module g.selected rect.terminal");
  let data_to_show = (selected_terminal.empty()) ? null : selected_terminal.attr("terminal_id");
  editor._active_terminal = data_to_show;
  let i = editor._active_node;
  let active_module = active_template.modules[i];
  let module_def = editor._module_defs[active_module.module];
  let fileinfos = (module_def.fields || []).filter(f => (f.datatype == 'fileinfo'));
  filebrowser.instance.blocked = (fileinfos.length < 1);
  
  var terminals_to_calculate = module_def.inputs.map(function(inp) {return inp.id});
  var fields_in = {};
  if (data_to_show != null && terminals_to_calculate.indexOf(data_to_show) < 0) {
    terminals_to_calculate.push(data_to_show);
  }
  let recalc_mtimes = app.settings.check_mtimes.value;
  let params_to_calc = terminals_to_calculate.map(function(terminal_id) {
    return {template: active_template, config: {}, node: i, terminal: terminal_id, return_type: "plottable"}
  })
  editor.calculate(params_to_calc, recalc_mtimes)
    .then(function(results) {
    var inputs_map = {};
    var id;
    results.forEach(function(r, ii) {
      id = terminals_to_calculate[ii];
      inputs_map[id] = r;
    })
    return inputs_map
  }).then(async function(im) {
    var datasets_in = im[data_to_show];
    var field_inputs = module_def.inputs
      .filter(function(d) {return /\.params$/.test(d.datatype)})
      .map(function(d) {return im[d.id]});
    field_inputs.forEach(function(d) {
      d.values.forEach(function(v) {
        extend(true, fields_in, v.params);
      });
    });
    await editor.show_plots([datasets_in]);
    fieldUI.instance.num_datasets_in = ((datasets_in || {}).values || []).length;
    fieldUI.instance.module = active_module;
    fieldUI.instance.reset_local_config();

    fieldUI.instance.module_id = i;
    fieldUI.instance.terminal_id = data_to_show;
    fieldUI.instance.module_def = module_def;
    fieldUI.instance.timestamp = Date.now();

    fieldUI.instance.auto_accept = app.settings.auto_accept;
  });
}

editor.module_clicked_single = module_clicked_single;

editor.get_full = function() {
  console.log(this._active_node, this._active_template, this._active_terminal);
  let params_to_calc = {
    template: this._active_template,
    config: {},
    node: this._active_node,
    terminal: this._active_terminal,
    return_type: "full"
  }
  this.calculate(params_to_calc, true).then(function(result) {
    console.log(result);
  })
}

function module_clicked() {
  var editor_select = d3.select("#" + editor._target_id);
  if (editor_select.selectAll("g.module g.selected rect.terminal").size() > 1) {
    module_clicked_multiple();
  }
  else {
    module_clicked_single();
  }
}
editor.module_clicked = module_clicked;
editor.handle_module_clicked = function(d,i,current_group,clicked_elem) {
  // d module data, i is module index, elem is registered to catch event
  //
  // Flow: 
  //  - if the module title is clicked, show configuration and 
  //    data from the first input terminal.
  //  - if input terminal is clicked, show that data and configuration
  //  - if output terminal is clicked, show that data and configuration
  
  var editor_select = d3.select("#" + editor._target_id);
  var elem = this; // this function is called from the context of a select.on   
  var clicked_elem = clicked_elem || d3.event.target;
  var multiple_select = (d3.event && (d3.event.shiftKey || d3.event.ctrlKey));
  var data_to_show;
  
  // clear all the stashed items, since we are plotting from the template again
  d3.selectAll("#stashedlist input.compare").property("checked", false);
  
  if (multiple_select) {
    var active_node = i,
        active_terminal = d3.select(clicked_elem).attr("terminal_id");
    if (!d3.select(clicked_elem).classed("terminal")) {
      console.log("can't select multiple module configs, just inputs and outputs");
      return
    }
    var parent = d3.select(clicked_elem.parentNode);
    parent.classed("selected", !(parent.classed("selected")));
    editor_select.selectAll("g.module, g.module g.title").classed("selected", false);
    module_clicked_multiple();   
  }

  else {
    editor_select.selectAll(".module .selected").classed("selected", false);
    d3.select(clicked_elem.parentNode).classed("selected", true);
    
    var active_template = editor._active_template;
    var active_module = active_template.modules[i];
    var module_def = editor._module_defs[active_module.module];
    var fields = module_def.fields || [];
    if (fields.filter(function(d) {return d.datatype == 'fileinfo'}).length == 0) {
        // var nav = $("#datasources");
        // nav.find("div.block-overlay").show();
    }
    
    if (d3.select(clicked_elem).classed("title")) {
      // then it's the module title clicked - 
      // select the first input terminal to show data from (if any)
      data_to_show = (module_def.inputs[0] || {}).id;  // second part undefined if no inputs
      // also highlight the first input terminal, if it's there:
      d3.select(elem).selectAll("g")
        .filter(function(d) { return d.id == data_to_show })
        .classed("selected", true);
    }
    else {
      // it's a terminal - show the data in it with the configuration
      //var side = d3.select(clicked_elem).classed("input") ? "input" : "output";
      data_to_show = d3.select(clicked_elem).attr("terminal_id");
      // also mark title of module as selected:
      d3.select(elem).select("g.title").classed("selected", true);
    }
    
    
    editor._active_node = i;
    editor._active_terminal = data_to_show;

    module_clicked();
  }
}

function compare_in_template(to_compare, template) {
  var template = template || editor._active_template;
  let recalc_mtimes = app.settings.check_mtimes.value;
  let params_to_calc = to_compare.map(function(a) {
        return {template: template, config: {}, node: a.node, terminal: a.terminal, return_type: "plottable"}
      });
  return editor.calculate(params_to_calc, recalc_mtimes)
    .then(function(results) {
      editor.show_plots(results);
    });
}

editor.show_plots = async function(results) {
  var new_plotdata;
  if (results.length == 0 || results[0] == null || results[0].values.length == 0) { 
    new_plotdata = null; 
  }
  else { 
    new_plotdata = {values: [], type: null, xcol: null, ycol: null}
    new_plotdata.type = results[0].values[0].type;
    results.forEach(function(r) {
      var values = r.values || [];
      values.forEach(function(v) {
        if (new_plotdata.type == null && v.type) {
          new_plotdata.type = v.type;
        }
        new_plotdata.values.push(v);
      });
    });
  }
    if (new_plotdata == null) {
      await plotter.instance.setPlotData({type: 'null'});
    }
    else if (['nd', '1d', '2d', '2d_multi', 'params', 'metadata'].includes(new_plotdata.type)) {
      await plotter.instance.setPlotData(new_plotdata);
    }
  }

editor.stash_data = function(suggested_name) {
  // embed the active template in a subroutine, exposing the
  // currently active output.  Store the structure in the 
  // browser.
  try {
      if (!window.localStorage) { throw false; }
  } catch (e) {
    alert("localStorage not supported in your browser");
    return;
  }
  if (editor._active_terminal == null) {
    alert("please select one input or output terminal to stash"); 
    return 
  }
  
  var suggested_name = (suggested_name == null) ?  "processed" : suggested_name;
  var stashname = prompt("stash data as:", suggested_name);
  if (stashname == null) {return} // cancelled
  
  var existing_stashes = _fetch_stashes();
  //var existing_stashnames = Object.keys(existing_stashes);
  
  if (existing_stashes.hasOwnProperty(stashname)) {
    var overwrite = confirm("stash named " + stashname + " already exists.  Overwrite?");
    if (!overwrite) {return}
  }
  
  var w = editor,
    node = w._active_node,
    terminal = w._active_terminal,
    template = w._active_template,
    instrument_id = w._instrument_id;
  var template_copy = extend(true, {}, template);
  var subroutine = {};
  subroutine.module = "user.stashed"
  subroutine.title = stashname;
  subroutine.module_def = {
    "template": template_copy,
    "inputs": [],
    "fields": [],
    "outputs": [{"source_module": node, "source_terminal": terminal, "terminal_id": "stashed"}],
    "action_id": "subroutine",
    "description": "previously processed data",
    "instrument_id": instrument_id
  }
  existing_stashes[stashname] = subroutine;
  _save_stashes(existing_stashes);
  editor.load_stashes(existing_stashes);
}

editor.load_stashes = function(stashes) {
  var existing_stashes = stashes || _fetch_stashes();
  var stashnames = Object.keys(existing_stashes);
  filebrowser.instance.stashnames = stashnames;
}

function _fetch_stashes() {
  try {
    return JSON.parse(localStorage['webreduce.editor.stashes'] || "{}");
  } catch (e) {
    return {}
  }
}
function _save_stashes(stashes) {
  try {
    localStorage['webreduce.editor.stashes'] = JSON.stringify(stashes);
  } catch (e) {}
}
editor.remove_stash = function(stashname) {
  var existing_stashes = _fetch_stashes();
  if (stashname in existing_stashes) {
    delete existing_stashes[stashname];
    _save_stashes(existing_stashes);
    editor.load_stashes();
  }
}

editor.reload_stash = function(stashname) {
  var overwrite = confirm("discard active template to load stashed?");
  if (!overwrite) {return}
  var existing_stashes = JSON.parse(localStorage['webreduce.editor.stashes'] || "{}");
  if (stashname in existing_stashes) {
    var stashed = existing_stashes[stashname];
    var template = stashed.module_def.template;
    var node = stashed.module_def.outputs[0].source_module;
    var terminal = stashed.module_def.outputs[0].source_terminal;
    var instrument_id = stashed.module_def.instrument_id;
    editor.load_template(template, node, terminal, instrument_id);
  }
}

editor.compare_stashed = function(stashnames) {
  // stashnames is a list of stashed data ids
  // eventually send these as-is to server, but for now since the server
  // doesn't handle subroutines...
  d3.selectAll("g.module .selected").classed("selected", false);
  var existing_stashes = _fetch_stashes();
  var stashnames = stashnames.filter(function(s) {return (s in existing_stashes)});
  var recalc_mtimes = app.settings.check_mtimes.value;
  var params_to_calc = stashnames.map(function(stashname) {
    var stashed = existing_stashes[stashname];
    return {
      template: stashed.module_def.template,
      config: {},
      node: stashed.module_def.outputs[0].source_module,
      terminal: stashed.module_def.outputs[0].source_terminal,
      return_type: "plottable"
    }
  });
  return editor.calculate(params_to_calc, recalc_mtimes)
    .then(function(results) {
      if (results.length < 1) { return }
      var first = results[0];
      for (var i=1; i<results.length; i++) {
        if (results[i].datatype == first.datatype) {
          first.values = first.values.concat(results[i].values);
        }
      }
      editor.show_plots([first]);
    });
}

editor.get_versioned_template = function(template) {
  var versioned = extend(true, {}, template),
      editor = this,
      module_list = versioned.modules;
  module_list.forEach(function(m) {
    if (m.module && m.module in editor._module_defs) {
      m.version = editor._module_defs[m.module].version;
    }
  });
  return versioned
}

editor.get_cached_timestamps = function() {
  var cache = this._cache;
  return this._cache.allDocs({"include_docs": true})
    .then(function(res) {
      return res.rows.map(function(r) {return [r.doc.created_at, r.doc._id]})
    })
}

editor.get_signature = function(params) {
  var template = params.template,
      config = params.config || {},
      node = params.node,
      terminal = params.terminal,
      return_type = params.return_type || 'metadata',
      export_type = params.export_type || 'column',
      concatenate = params.concatenate || false;
  
  var versioned = this.get_versioned_template(template), 
      sig = sha1(JSON.stringify({
        method: "calculate",
        template: versioned,
        config: config,
        node: node,
        terminal: terminal,
        return_type: return_type, 
        export_type: export_type,
        concatenate: concatenate}));
        
  return sig
}

async function calculate_one(params, caching) {
  var r = new Promise(function(resolve, reject) {resolve()});
  var template = params.template,
        config = params.config || {},
        node = params.node,
        terminal = params.terminal,
        return_type = params.return_type || 'metadata',
        export_type = params.export_type || 'column',
        concatenate = params.concatenate || false;
      
  if (caching) {
    var sig = editor.get_signature(params);
    r = r.then(function() { 
      return editor._cache.get(sig).then(function(cached) {return cached.value})
      .catch(function(e) {
        var versioned = editor.get_versioned_template(template);
        return server_api.calc_terminal({
            template_def: versioned,
            config: config,
            nodenum: node,
            terminal_id: terminal,
            return_type: return_type,
            export_type: export_type,
            concatenate: concatenate
          })
          .then(function(result) {
            var doc = {
              _id: sig, 
              created_at: Date.now(),
              value: result 
            }
            editor._cache.put(doc);
            return result
          })
          .catch(function(e) {
            console.log("error", e)
          })
      })
    })
  } else {
    r = r.then(function() { return server_api.calc_terminal({
      template_def: template,
      config: config,
      nodenum: node,
      terminal_id: terminal,
      return_type: return_type,
      export_type: export_type,
      concatenate: concatenate});
    })
    .catch(function(e) {
      console.log("error", e)
    });
  }
  return r
}

editor.calculate = async function(params, recalc_mtimes, noblock, result_callback) {
  //var recalc_mtimes = $("#auto_reload_mtimes").prop("checked");
  // call result_callback on each result individually (this function will return all results
  // if you want to act on the aggregate after)
  var caching = app.settings.cache_calculations.value;
  app_header.instance.calculation_progress.done = 0;
  app_header.instance.$off("cancel-calculation"); // clear previous handlers
  editor._calculation_cancelled = false;
  var calculation_finished = false;
  var r = Promise.resolve();
  var cancel_promise = new Promise(function(resolve, reject) { 
    app_header.instance.$on("cancel-calculation", function() {
      editor._calculation_cancelled = true;
      calculation_finished = true;
      resolve({"cancelled": true});
    });
  });
  
  let results = [];
  if (!noblock) {
    app_header.instance.calculation_progress.visible = true;
  }
  try {
    if (recalc_mtimes) {
      await Promise.race([cancel_promise, app.update_file_mtimes()]);
    }
    if (params instanceof Array) {
      app_header.instance.calculation_progress.total = params.length;
      for (let i=0; i<params.length; i++) {
        let p = params[i];
        if (!editor._calculation_cancelled) {
          let result = await Promise.race([cancel_promise, calculate_one(p, caching)]);
          if (result_callback) { await result_callback(r, p, i); }
          app_header.instance.calculation_progress.done = i+1;
          results.push(result);
        }
      }
    }
    else {
      results = await Promise.race([cancel_promise, calculate_one(params, caching)]);
    }
  } catch(err) {

  } finally {
    app_header.instance.calculation_progress.visible = false;
  }
  return results;
}

var export_handlers = {
    
  download: function(result, filename) {
    if (result.values.length == 1) {
      app.download(result.values[0].value, filename);
    }
    else {
      var filect = 0;
      let subnames = new Set();
      let subcounter = 0;
      var write_next = function(writer, exports) {
        if (filect < exports.length) {
          var to_export = exports[filect++];
          let test_subname = to_export.filename || "default_filename";
          var subname = test_subname;
          while (subnames.has(subname)) {
            subname = test_subname + "_" + (subcounter++).toFixed();
          }
          subnames.add(subname);
          var reader = new zip.TextReader(to_export.value);
          writer.add(subname, reader, function() { write_next(writer, exports); });
        }
        else { 
          writer.close(function(blob) {
            app.download(blob, filename + ".zip");
          });
        }
      }
      return zip.createWriter(new zip.BlobWriter("application/zip"), function(writer) {
          write_next(writer, result.values);
        }, function(error) {
          console.log(error);
        });
    }
  },
    
  webapi: function(result, filename, data) {
      window.addEventListener("message", connection_callback, false);
      var connection_id = Math.random().toString(36).replace(/[^a-z]+/g, '').substr(0, 5);
      var webapp = window.open(data.url + "?connection_id=" + connection_id, "_blank");
      var exported = result.values.map(function(v) { return v.value }).join("\n\n");
      function connection_callback(event) {
        // hoisting is required... 
        var message = event.data;
        if (message.connection_id == connection_id) {
          window.removeEventListener("message", arguments.callee);
          if (message.ready) {
            webapp.postMessage({method: data.method, args: [exported], connection_id: connection_id}, "*");
          }
        }
      }
  }
}

function isObject(val) { return typeof val === 'object' && !Array.isArray(val) };
function get_all_keys(obj) {
  var keys = Object.keys(obj);
  keys = keys.filter(function (k) { return !Array.isArray(obj[k]) });
  var output_keys = [];
  keys.forEach(function (k) {
    if (obj[k] && isObject(obj[k])) {
      output_keys.push([k, get_all_keys(obj[k])]);
    }
    else {
      output_keys.push([k]);
    }
  });
  return output_keys.sort();
}

editor.export_targets = [
  { 
    "id": "download",
    "label": "download",
    "type": "download"
  }
];

editor.export_data = function() {
  var w = editor;
  if (w._active_terminal == null) { alert("no input or output selected to export"); }
  let active_modulename = w._active_template.modules[w._active_node].module;
  let active_module_def = editor._instrument_def.modules.find(function(m) { return m.id == active_modulename })
  let active_input_output = active_module_def.inputs
    .concat(active_module_def.outputs)
    .find(function(o) { return o.id == w._active_terminal});
  let export_datatype = active_input_output.datatype;

  var export_types = editor._instrument_def.datatypes.find(function(d) { return d.id == export_datatype}).export_types;
  var params = {
    template: w._active_template,
    config: {},
    node: w._active_node,
    terminal: w._active_terminal,
    return_type: "export",
    //export_type: export_type,
    concatenate: true
  }
  if (export_types.length == 0) {
    alert('no exports defined for this datatype: ' + export_datatype);
    return
  }
  /*
  else if (export_types.length == 1) {
    // if there's only one, no need to ask...
    params.export_type = export_types[0];
    initiate_export(params);
  }
  */
  else {
    // when there are more than one export types defined, ask which one to use:
    export_dialog.instance.open(export_types);
    export_dialog.instance.$once("export-select", async function(export_type, concatenate) {
      var w = editor;
      var recalc_mtimes = app.settings.check_mtimes.value;
      params.export_type = export_type;
      params.concatenate = concatenate;
      let exported = await editor.calculate(params, recalc_mtimes, true);
      let suggested_name = (exported.values[0] || {}).filename || "myfile.refl";
      let additional_export_targets = w.instruments[w._instrument_id].export_targets || [];
      let export_targets = w.export_targets.concat(additional_export_targets);
      export_dialog.instance.export_targets = export_targets;
      export_dialog.instance.retrieved(suggested_name);
      export_dialog.instance.$once("export-route", function(filename, target) {
        export_handlers[target.type](exported, filename, target.data || {});
      })
    });
  }

}


editor.update_completions = function() {
  var satisfactions = dependencies.mark_satisfied(this._active_template, this._module_defs);
  var wires = this._active_template.wires;
  var svg = this._instance.svg();
  svg.selectAll("path.wire").classed("filled", function(d,i) { return satisfactions.wires_satisfied.has(i); });
  svg.selectAll("g.module").each(function(d,i) {
    d3.select(this).selectAll("rect.terminal.output").style("fill", (satisfactions.modules_satisfied.has(i)) ? null : "url(#output_hatch)");
  })
  svg.selectAll("rect.terminal.input").style("fill", "url(#input_hatch)");
  svg.selectAll("rect.terminal.input").each(function(d,i) {
    var term = d3.select(this);
    var id = term.attr("terminal_id");
    var node = d3.select(this.parentNode.parentNode).attr("index");
    wires.forEach(function(w,i) { 
      var mine = (w.target[0] == node && w.target[1] == id);
      if (mine && satisfactions.wires_satisfied.has(i)) {
        term.style("fill", null);
      }
    });
  });
}

editor.load_instrument = async function(instrument_id) {
  editor._instrument_id = instrument_id;
  let instrument_def = await server_api.get_instrument({instrument_id});
  editor._instrument_def = instrument_def;
  editor._module_defs = Object.fromEntries((instrument_def.modules || []).map(m => (
    [m.id, m]
  )));
  // load into the editor instance
  editor._instance.module_defs(editor._module_defs);
  // pass it through:
  return instrument_def;
}

editor.switch_instrument = async function(instrument_id, load_default=true) {
  // load_default_template is a boolean: true if you want to do that action
  // (defaults to true)
  if (instrument_id !== editor._instrument_id) {
    let instrument_def = await this.load_instrument(instrument_id);
    let categories = editor.instruments[instrument_id].categories;
    let old_categories = vueMenu.instance.categories;
    old_categories.splice(0, old_categories.length, ...categories);
    vueMenu.instance.predefined_templates = Object.keys(instrument_def.templates || {});
    vueMenu.instance.current_instrument = instrument_id;
    let template_names = Object.keys(instrument_def.templates);
    let default_template = template_names[0];
    if (localStorage) {
      var lookup_id = "webreduce.instruments." + instrument_id + ".last_used_template";
      var test_template_name = localStorage.getItem(lookup_id);
      if (test_template_name != null && test_template_name in instrument_def.templates) {
        default_template = test_template_name;
      }
    }
    if (load_default) {
      app.current_instrument = instrument_id;
      var template_copy = extend(true, {}, instrument_def.templates[default_template]);
      return editor.load_template(template_copy);
    }
  } 
}

editor.edit_template = function(template_def, instrument_id) {
  var template_def = template_def || this._active_template;
  var instrument_id = instrument_id || this._instrument_id;
  var post_load = function() {
    var te = editor._active_template_editor;
    te.load_instrument(instrument_id)
        .then(function(){
          te.e.import(template_def, true);
          te.e.add_brush();
        })
    d3.select(te.document.getElementById("apply_changes")).on('click', function() {
      editor.load_template(te.e.export(), null, null, instrument_id);
    });
  }
  if (this._active_template_editor == null || this._active_template_editor.closed) {
    var te = window.open(template_editor_url, "template_editor", "width=960,height=480");
    this._active_template_editor = te;
    te.addEventListener('editor_ready', post_load, false);
  }
}

editor.load_template = async function(template_def, selected_module, selected_terminal, instrument_id) {
  var we = this;
  var instrument_id = instrument_id || we._instrument_id;
  await editor.switch_instrument(instrument_id, false);
  editor._active_template = template_def;
  //var r = we.switch_instrument(instrument_id, false).then(function() {
      
  let template_sourcepaths = filebrowser.getAllTemplateSourcePaths(template_def);
  let browser_sourcepaths = filebrowser.getAllBrowserSourcePaths();
    var sources_loaded = Promise.resolve();
  Object.entries(template_sourcepaths).forEach(async ([source, pathobj]) => {
    let paths = Object.keys(pathobj);
    paths.forEach(async (path) => {
      if (browser_sourcepaths.findIndex(sp => (sp.source == source && sp.path == path)) < 0) {
        await filebrowser.addDataSource(source, path.split("/"));
      }
    })
  })
    
  var target = d3.select("#" + we._target_id);    
  we._instance.import(template_def);

  target.selectAll(".module").classed("draggable wireable", false);
  target.selectAll("g.module").on("click", editor.handle_module_clicked);
  //target.selectAll("g.module").on("contextmenu", editor.handle_module_contextmenu);
  
  var autoselected = template_def.modules.findIndex(function(m) {
    var has_fileinfo = editor._module_defs[m.module].fields
      .findIndex(function(f) {return f.datatype == 'fileinfo'}) > -1
    return has_fileinfo;
  });
  
  if (selected_module != null) {
    autoselected = selected_module;
  }
  
  if (autoselected > -1) {
    var toselect = target.selectAll('.module')
      .filter(function(d,i) { return i == autoselected })
    // choose the module directly by default
    var toselect_target = toselect.select(".title").node();
    // but if a terminal is specified, use that as target instead.
    if (selected_terminal != null) {
      var term = toselect.select('rect.terminal[terminal_id="'+selected_terminal+'"]').node();
      if (term != null) {toselect_target = term} // override the selection with terminal
    }
    
    await editor.handle_module_clicked.call(toselect.node(), toselect.datum(), autoselected, null, toselect_target);
    await editor.update_completions();
  }
  app.autoselected = autoselected;  
}

editor.load_metadata = async function(files_metadata, datasource, path) {
  var instrument_id = editor._instrument_id;
  var instrument = editor.instruments[instrument_id];
  var file_objs = {};
  var files_filter = instrument.files_filter || function(x) {return true};
  var files = Object.keys(files_metadata);
  var datafiles = files.filter(files_filter);

  ////////////////////////////////////////////////////////////////////////////
  // Send rpc requests one after the other to the server
  ////////////////////////////////////////////////////////////////////////////
  var load_params = datafiles.map(function(j) {
    return {
      "source": datasource,
      "path": path + "/" + j,
      "mtime": files_metadata[j].mtime
    }
  });

  let loader_template = instrument.load_file(load_params, file_objs, false, 'metadata');
  let results = await editor.calculate(loader_template, false, false);
  results.forEach(function(result, i) {
    var lp = load_params[i];
    if (result && result.values) {
      result.values.forEach(function(v) {v.mtime = lp.mtime});
      file_objs[lp.path] = result;
    }
  });
  
  editor._datafiles = results;
  return file_objs;
}