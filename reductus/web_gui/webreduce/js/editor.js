export var editor = {};

import { app } from './main.js';
import {server_api} from './server_api/api_msgpack.js';
import {dependencies} from './deps.js';
import {instruments} from './instruments/index.js';
// now a global...
import {zip} from './libraries.js';
import { Vue } from './libraries.js';
import {extend, dataflowEditor} from './libraries.js';
import { Cache } from './idb_cache.js';
import { sha1 } from './libraries.js';
import {filebrowser} from './filebrowser.js';
//import {make_fieldUI} from './fieldUI.js';
import { fieldUI } from './ui_components/fields_panel.js';
import { plotter  } from './plot.js';
import { vueMenu } from './menu.js';
import { export_dialog } from './ui_components/export_dialog.js';
import { app_header } from './app_header.js';
import { DataflowViewer } from './ui_components/dataflow_viewer.js';

const MAX_CACHE_AGE = 90; // days

editor.instruments = instruments;

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
  set(key, value) {
    return this.storage.set(key, value);
  }
};



editor.make_cache = async function() {
  try {
    this._cache = new Cache();
    this._cache.remove_older(Date.now() - MAX_CACHE_AGE * 24 * 60 * 60 * 1000);
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

// TODO: remove when everyone has updated
// REMOVE OLD DEPRECATED POUCHDB
window.indexedDB.deleteDatabase("_pouch_calculations");

editor.clear_cache = async function() {
  app_header.instance.show_snackbar("clearing cache...", 4000);
  await this._cache.clear();
  app_header.instance.show_snackbar("cache cleared", 4000);
}

editor.create_instance = function(target_id) {
  // create an instance of the dataflow editor in
  // the html element referenced by target_id
  let target = document.getElementById(target_id);
  const DataflowViewerClass = Vue.extend(DataflowViewer);
  this.instance_container = target.parentElement;
  this.instance = new DataflowViewerClass({
    propsData: {instrument_def: {}},
    methods: {
      on_select: editor.module_clicked,
      on_change: editor.update_completions,
    }
  }).$mount(target);
  // TODO: make fields respond to "enter" key by advancing to next
  // module in template? (accept on enter)
}

function module_clicked_multiple() {
  app.hide_fields();
  compare_in_template(editor.instance.selected.terminals, editor.instance.template_data);
}

editor.advance_to_output = function() {
  let sm = editor.instance.selected.modules;
  if (sm.length == 1) {
    // can only advance to output if exactly one module is selected
    let module_index = sm[0];
    let module = editor.instance.template_data.modules[module_index];
    let module_def = editor.instance.module_defs[module.module];
    let first_output = (module_def.outputs[0] || {}).id;
    if (first_output != null) {
      let st = editor.instance.selected.terminals;
      st.splice(0, st.length, [module_index, first_output]);
    }
  }
  module_clicked_single();
}

function module_clicked_single() {
  app.show_fields();
  let active_template = editor.instance.template_data;
  let selected_terminal = editor.instance.selected.terminals[0];
  let data_to_show = (selected_terminal || [])[1];
  editor._active_terminal = data_to_show;
  let i = editor.instance.selected.modules[0];
  let active_module = editor.instance.template_data.modules[i];
  let module_def = editor.instance.module_defs[active_module.module];
  let fileinfos = (module_def.fields || []).filter(f => (f.datatype == 'fileinfo'));
  filebrowser.instance.blocked = (fileinfos.length < 1);
  
  var terminals_to_calculate = module_def.inputs
    .filter(function(inp) {return /\.params$/.test(inp.datatype)})
    .map(function(inp) {return inp.id});
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
  let params_to_calc = this.instance.selected.terminals.map(([node, terminal]) => ({
    template: this.instance.template_data,
    config: {},
    node,
    terminal,
    return_type: "full"
  }));
  return this.calculate(params_to_calc, true).then(function(result) {
    console.log(result);
    return result;
  })
}

function module_clicked() {
  let nterms = editor.instance.selected.terminals.length;
  if (nterms > 0) {
    filebrowser.instance.selected_stashes.splice(0);
    if (nterms > 1) {
      module_clicked_multiple();
    }
    else {
      module_clicked_single();
    }
  }
  else if(editor.instance.selected.modules.length > 1) {
    app.hide_fields();
    filebrowser.instance.blocked = true;
  }
}

editor.module_clicked = module_clicked;

async function compare_in_template(to_compare, template) {
  var template = template || editor.instance.template_data;
  let recalc_mtimes = app.settings.check_mtimes.value;
  let params_to_calc = to_compare.map(([node, terminal]) => ({
        template,
        config: {}, 
        node,
        terminal,
        return_type: "plottable"
  }));
  let results = await editor.calculate(params_to_calc, recalc_mtimes);
  editor.show_plots(results);
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
  if (editor.instance.selected.terminals.length != 1) {
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
  
  let [node, terminal] = editor.instance.selected.terminals[0];
  let template = editor.instance.template_data;
  let instrument_id = editor._instrument_id;
  let template_copy = extend(true, {}, template);
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
  this.instance.selected.modules.splice(0); 
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

// NOTE: crypto.subtle only works on https connections
// async function digestMessage(message, algorithm="SHA-256") {
//   const msgUint8 = new TextEncoder().encode(message);                           // encode as (utf-8) Uint8Array
//   const hashBuffer = await crypto.subtle.digest(algorithm, msgUint8);           // hash the message
//   const hashArray = Array.from(new Uint8Array(hashBuffer));                     // convert buffer to byte array
//   const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join(''); // convert bytes to hex string
//   return hashHex;
// }

async function digestMessage(message, algorithm="SHA-1") {
  // only SHA-1 is support in this implementation
  return sha1(message);
}

editor.get_signature = async function(params) {
  const config = params.config ?? {};
  const { node, terminal, template } = params;
  const return_type = params.return_type ?? 'metadata';
  const export_type = params.export_type ?? 'column';
  const concatenate = params.concatenate ?? false;
  
  const versioned = this.get_versioned_template(template);
  const sig = await digestMessage(JSON.stringify({
        method: "calculate",
        template: versioned,
        config: config,
        node: node,
        terminal: terminal,
        return_type: return_type, 
        export_type: export_type,
        concatenate: concatenate}), "SHA-1");
        
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
    r = r.then(function() {
        return editor.get_signature(params);
    })
    .then(function(sig) {
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
            editor._cache.set(sig, doc);
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
    
  download: async function(result, filename) {
    if (result.values.length == 1) {
      app.download(result.values[0].value, filename);
    }
    else {
      let subnames = new Set();
      let subcounter = 0;
      const zipWriter = new zip.ZipWriter(new zip.BlobWriter("application/zip"));
      for (let item of result.values) {
        let test_subname = item.filename || "default_filename";
        let subname = test_subname;
        while (subnames.has(subname)) {
          subname = `${test_subname}_${subcounter++}`;
        }
        subnames.add(subname);
        await zipWriter.add(subname, new zip.TextReader(item.value));
      }
      let blob = await zipWriter.close();
      app.download(blob, `${filename}.zip`);
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
          window.removeEventListener("message", connection_callback);
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
  let {modules, terminals} = this.instance.selected;

  if (terminals.length == 0) { alert("no input or output selected to export"); return }
  if (terminals.length > 1) { alert("more than one input or output selected to export"); return }
  let [node, terminal] = terminals[0];
  let template = this.instance.template_data;
  let module = this.instance.template_data.modules[node];
  let module_def = this.instance.module_defs[module.module];

  let active_input_output = module_def.inputs
    .concat(module_def.outputs)
    .find(function(o) { return o.id == terminal});
  let export_datatype = active_input_output.datatype;

  let export_types = this.instance.instrument_def.datatypes.find(function(d) { return d.id == export_datatype }).export_types;
  var params = {
    template,
    config: {},
    node,
    terminal,
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
        export_handlers[target.type](exported, filename, target || {});
      })
    });
  }

}


editor.update_completions = function() {
  var satisfactions = dependencies.mark_satisfied(editor.instance.template_data, editor.instance.module_defs);
  editor.instance.satisfied.wires = Array.from(satisfactions.wires_satisfied.values());
  editor.instance.satisfied.modules = Array.from(satisfactions.modules_satisfied.values());
  let sterminals = [];
  editor.instance.template_data.wires
    .filter((w,i) => satisfactions.wires_satisfied.has(i))
    .forEach((w,i) => {
      sterminals.push(w.source, w.target)
  });
  editor.instance.satisfied.terminals = sterminals;
}

editor.load_instrument = async function(instrument_id) {
  editor._instrument_id = instrument_id;
  let instrument_def = await server_api.get_instrument({instrument_id});
  editor._instrument_def = instrument_def;
  let module_defs = Object.fromEntries((instrument_def.modules || []).map(m => (
    [m.id, m]
  )));
  // load into the editor instance
  editor._module_defs = module_defs;
  editor.instance.$set(editor.instance, 'instrument_def', instrument_def);
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
    vueMenu.instance.default_categories = extend(true, [], categories);
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

editor.load_template = async function(template_def, selected_module, selected_terminal, instrument_id) {
  var instrument_id = instrument_id || this._instrument_id;
  await editor.switch_instrument(instrument_id, false);
  editor._active_template = template_def;
  //var r = this.switch_instrument(instrument_id, false).then(function() {
      
  let template_sourcepaths = filebrowser.getAllTemplateSourcePaths(template_def);
  let browser_sourcepaths = filebrowser.getAllBrowserSourcePaths();
  var sources_loaded = Promise.resolve();
  for (let [source, pathobj] of Object.entries(template_sourcepaths)) {
    let paths = Object.keys(pathobj);
    for (let path of paths) {
      if (browser_sourcepaths.findIndex(sp => (sp.source == source && sp.path == path)) < 0) {
        await filebrowser.addDataSource(source, path.split("/"));
      }
    }
  }
    
  this.instance.template_data = template_def;
  this.instance.$nextTick(() => this.instance.fit_module_text());
  
  let autoselected = selected_module;
  let autoselected_term = selected_terminal || {};
  if (autoselected == null) {
    autoselected = template_def.modules.findIndex(function(m) {
        var has_fileinfo = editor._module_defs[m.module].fields
          .findIndex(function(f) {return f.datatype == 'fileinfo'}) > -1
        return has_fileinfo;
      });
  }
  
  if (autoselected > -1) {
    let sm = this.instance.selected.modules;
    let st = this.instance.selected.terminals;
    sm.splice(0, sm.length, autoselected);
    // choose the module directly by default
    // but if a terminal is specified, use that as target instead.
    st.splice(0, st.length, [selected_module, selected_terminal]);
    await editor.update_completions();
  }
  this.instance.on_select();
  app.resize_bottom(this.instance.get_bbox());
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
  try {
    vueMenu.instance.category_keys = get_all_keys(results[0]["values"][0])
  }
  catch(e) {}
  return file_objs;
}
