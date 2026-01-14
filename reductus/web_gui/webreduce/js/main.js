"use strict";
// SIDE-EFFECTS ONLY FOR NOW...
import { createApp } from 'vue';
import Split from 'split.js';
import { emitter } from './bus.js';
import { editor } from './editor.js';
import { server_api } from './server_api/api_msgpack.js';
import { filebrowser } from './filebrowser.js';
import { plotter } from './plot.js';
import { FieldsPanel } from './ui_components/fields_panel.js';
import { vueMenu } from './menu.js';
import { export_dialog } from './ui_components/export_dialog.js';
import { reload } from './reload.js';
import { headerComponent } from './app_header.js';

export const app = {}; // put state here.

var active_reduction = {
  "config": {},
  "template": {}
}
app.current_instrument = "ncnr.refl";
app.stored_layout_sizes = null;

var statusline_log = function (message) {
  var statusline = document.getElementById("statusline");
  if (statusline && statusline.innerHTML) {
    statusline.innerHTML = message;
  }
}

app.statusline_log = statusline_log;

function getUrlVars() {
  var vars = [], hash;
  var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
  for (var i = 0; i < hashes.length; i++) {
    hash = hashes[i].split('=');
    vars.push(hash);
  }
  return vars;
}

app.callbacks = {};
app.callbacks.resize_center = function () { };

window.onbeforeunload = function (e) {
  var e = e || window.event;
  var msg = "Do you really want to leave this page?"

  // For IE and Firefox
  if (e) {
    e.returnValue = msg;
  }

  // For Safari / chrome
  return msg;
};

function create_downloader() {
  var a = document.createElement("a");
  document.body.appendChild(a);
  a.style = "display: none";
  a.id = "savedata";
  return function (data, fileName) {
    var blob = (data instanceof Blob) ? data : new Blob([data], { type: "text/plain" });
    // IE 10 / 11
    if (window.navigator.msSaveOrOpenBlob) {
      window.navigator.msSaveOrOpenBlob(blob, fileName);
    } else {
      var url = window.URL.createObjectURL(blob);
      a.href = url;
      a.download = fileName;
      a.target = "_blank";
      //window.open(url, '_blank', fileName);
      a.click();
      setTimeout(function () { window.URL.revokeObjectURL(url) }, 1000);
    }
    // cleanup: this seems to break things!
    //document.body.removeChild(a);
  };
};

window.onpopstate = async function (e) {
  // called by load on Safari with null state, so be sure to skip it.
  //if (e.state) {
  let datasources = app._datasources || {};
  let url_vars = getUrlVars();
  let source = (datasources[0] || {}).name;
  let start_path = "";
  let instrument = app._instruments[0];

  url_vars.forEach(function (v, i) {
    if (v[0] == 'pathlist' && v[1] && v[1].length) {
      start_path = v[1];
    }
    else if (v[0] == 'source' && v[1]) {
      source = v[1];
    }
    else if (v[0] == 'instrument' && v[1]) {
      instrument = v[1];
    }
  })

  app.current_instrument = instrument;
  await editor.switch_instrument(instrument);
  editor.load_stashes();

  console.log("adding datasource:", source, " at path:", start_path);

  add_datasource(source, start_path);
}

function add_datasource(sourcename, start_path_in="") {
  let start_path = "";
  let datasource = app._datasources.find(d => (d.name == sourcename));
  if (start_path_in != "") {
    start_path = start_path_in;
  }
  else if (datasource && datasource.start_path) {
    start_path = datasource.start_path;
  }
  let pathlist = start_path.split("/");
  app.filebrowser_instance.addDataSource(sourcename, pathlist);
}

window.onload = async function () {
  window.app = app;
  app.download = create_downloader();
  window.editor = editor;
  //zip.workerScriptsPath = "js/";
  //zip.useWebWorkers = false;
  var middle_layout = Split(['.ui-layout-west', '.ui-layout-center', '.ui-layout-east'], {
    sizes: [25, 50, 25],
    elementStyle: (dimension, size, gutterSize) => ({
      'flex-basis': `calc(${size}% - ${gutterSize}px)`,
    }),
    gutterStyle: (dimension, gutterSize) => ({
      'flex-basis': `${gutterSize}px`,
    }),
    minSize: 0
  });
  app.layout = middle_layout;
  app.hide_fields = function() {
    // idempotent
    if (this.stored_layout_sizes == null) {
      fieldUI.visible = false;
      this.stored_layout_sizes = this.layout.getSizes();
      this.layout.collapse(2);
    }
  }
  app.show_fields = function() {
    if (this.stored_layout_sizes) {
      this.layout.setSizes(this.stored_layout_sizes);
      this.stored_layout_sizes = null;
      fieldUI.visible = true;
    }
  }
  //$("#menu").menu({width: '200px;', position: {my: "left top", at: "left+15 bottom"}});

  var layout = Split(["#middle_content", "#bottom_panel"], {
    sizes: [95, 5],
    // elementStyle: (dimension, size, gutterSize) => ({
    //   'flex-basis': `calc(${size}% - ${gutterSize}px)`,
    // }),
    // gutterStyle: (dimension, gutterSize) => ({
    //   'flex-basis': `${gutterSize}px`,
    // }),
    direction: 'vertical'
  })
  app.vertical_layout = layout;

  app.resize_bottom = function(bbox, border=10) {
    let full_height = app.vertical_layout.parent.offsetHeight;
    let box_height = bbox.y + bbox.height + border;
    let bpercent = box_height / full_height * 100.0;
    let tpercent = 100.0 - bpercent;
    app.vertical_layout.setSizes([tpercent, bpercent]);
  }

  await editor.create_instance("bottom_panel", emitter);
  const app_header = createApp(headerComponent, { emitter: emitter }).mount(document.getElementById("app_header"));
  console.log("app_header instance: ", app_header, app_header.$el);
  emitter.on("toggle-menu", () => {
    vueMenu.instance.showNavigation = !vueMenu.instance.showNavigation
  });

  // Wire up app_header events
  emitter.on("app_header.reset_progress", () => {
    app_header.calculation_progress.done = 0;
  });
  emitter.on("app_header.show_calculation_progress", (total) => {
    app_header.show_calculation_progress(total);
  });
  emitter.on("app_header.update_progress", (done, total) => {
    app_header.calculation_progress.done = done;
    app_header.calculation_progress.total = total;
  });
  emitter.on("app_header.close_calculation_progress", () => {
    app_header.close_calculation_progress();
  });
  emitter.on("app_header.show_snackbar", ({message, duration}) => {
    app_header.show_snackbar(message, duration);
  });

  await server_api.__init__(app_header.init_progress);
  //app_header.instance.init_progress.visible = false;
  server_api.exception_handler = api_exception_handler;
  app.server_api = server_api;

  const filebrowser_instance = createApp(filebrowser, {
    emitter: emitter
  }).mount(document.getElementById("filebrowser"));
  app.filebrowser_instance = filebrowser_instance;
  
  // Initialize file browser with default datasource
  if (app._datasources && app._datasources.length > 0) {
    const defaultDatasource = app._datasources[0];
    const defaultPath = [];
    await filebrowser_instance.addDataSource(defaultDatasource.name, defaultPath);
  }
  
  const filebrowser_actions = {
    remove_stash(stashname) {
      editor.remove_stash(stashname);
    },
    reload_stash(stashname) {
      editor.reload_stash(stashname);
    },
    compare_stashed(stashnames) {
      editor.compare_stashed(stashnames);
    }
  }
  emitter.on("filebrowser.action", (name, argument) => {
    if (filebrowser_actions[name]) {
      filebrowser_actions[name](argument);
    }
  });

  plotter.create_instance("centerpane", emitter);
  emitter.on("plotter.action", (name, argument) => {
    // there's only one action from plotter... export:
    if (name === 'export_data') {
      editor.export_data();
    }
  });
  app.plot_instance = plotter.instance;

  const fieldUI = createApp(FieldsPanel, { emitter: emitter }).mount(document.getElementById("east_panel"));
  emitter.on("fields.fileinfo_update", ({value, no_terminal_selected}) => {
    fieldUI.update_fileinfo(value, no_terminal_selected);
  });
  emitter.on("fields.update", () => {
    editor.update_completions();
  });
  emitter.on("fields.clear", () => {
    editor.module_clicked_single();
  });
  emitter.on("fields.accept_button", () => {
    editor.advance_to_output();
  });
  emitter.on("editor.calculate_single", (payload) => {
    fieldUI.set_calculator_single(payload);
  });
  
  vueMenu.create_instance("vue_menu", {enable_uploads: typeof ENABLE_UPLOADS !== 'undefined' && ENABLE_UPLOADS }, emitter);
  app.settings = vueMenu.instance.settings;
  const menu_actions = {
    new_template() {
      var empty_template = { modules: [], wires: [] };
      editor.edit_template(empty_template)
    },
    edit_template() { editor.instance.show_help() },
    download_template() {
      let filename = prompt("Save template as:", "template.json");
      if (filename != null) {
        app.download(JSON.stringify(editor._active_template, null, 2), filename);
      }
    },
    async upload_file(file) {
      //window.fheader = file.slice(0, 20).arrayBuffer();
      let template_data = await reload(file);
      editor.load_template(template_data.template, template_data.node, template_data.terminal, template_data.instrument_id);
    },
    async upload_datafiles(files) {
      await server_api.upload_datafiles(files);
      notify(`Uploaded: ${files.length} files`);
      app.filebrowser_instance.refreshAll();
    },
    load_predefined(template_id) {
      let instrument_id = editor._instrument_id;
      const template_copy = structuredClone(editor._instrument_def.predefined_templates[template_id]);
      editor.load_template(template_copy, null, null, instrument_id);
      // Remember this choice, to be used on next instrument switch:
      try {
        var lookup_id = "webreduce.instruments." + instrument_id + ".last_used_template";
        localStorage.setItem(lookup_id, template_id);
      } catch (e) {}
    },
    // data functions
    stash_data() { editor.stash_data() },
    set_categories(new_categories) {
      editor.instruments[editor._instrument_id].categories = new_categories;
      console.log(app.filebrowser_instance);
      app.filebrowser_instance.refreshAll();
    },
    export_data() { editor.export_data() },
    add_datasource,
    clear_cache() { editor.clear_cache() },
    switch_instrument(instrument_id) {
      editor.switch_instrument(instrument_id);
    }
  }
  emitter.on("vue_menu.action", (name, argument) => {
    if (menu_actions[name]) {
      menu_actions[name](argument);
    }
  });
  export_dialog.create_instance();


  // set up the communication between these panels:
  // fieldUI.fileinfoUpdateCallback = filebrowser.fileinfoUpdate;
  // filebrowser.fileinfoUpdateCallback = fieldUI.fileinfoUpdate;

  async function list_datasources() {
    let datasources = await server_api.list_datasources();
    app._datasources = datasources;
    vueMenu.instance.datasources = datasources.map(d => d.name);
    return datasources
  }


  async function list_instruments() {
    let instruments = await server_api.list_instruments();
    app._instruments = instruments;
    vueMenu.instance.instruments = instruments;
    return instruments;
  }

  app.update_file_mtimes = async function (template) {
    // modifies template in-place with new mtimes
    var template = template || editor._active_template;
    // First, generate a list of all sources/paths for getting needed info from server
    var fsp = filebrowser.getAllTemplateSourcePaths(template);

    // now step through the list of sources and paths and get the mtimes from the server:
    var times_promise = new Promise(function (resolve, reject) { resolve(null) });
    var updated_times = {};
    for (var source in fsp) {
      updated_times[source] = updated_times[source] || {};
      for (var path in fsp[source]) {
        let r = await server_api.get_file_metadata({ source: source, pathlist: path.split("/") });
        for (var fn in r.files_metadata) {
          let d = r.files_metadata[fn];
          updated_times[source][path + "/" + fn] = d.mtime;
        }
      }
    }

    template.modules.forEach(function (m, i) {
      var def = editor._module_defs[m.module];
      var fileinfo_fields = def.fields.filter(function (f) { return f.datatype == "fileinfo" })
        .map(function (f) { return f.id });
      fileinfo_fields.forEach(function (fname) {
        if (m.config && m.config[fname]) {
          m.config[fname].forEach(function (finfo) {
            var new_mtime = updated_times[finfo.source][finfo.path];
            if (finfo.mtime != new_mtime) {
              console.log(finfo.path + " old mtime=" + finfo.mtime + ", new mtime=" + new_mtime);
            }
            finfo.mtime = new_mtime;
          });
        }
      });
    });

    return
  }

  function api_exception_handler(exc) {
    console.log("api exception: ", exc);
    var message = exc.exception || "no error message";
    notify("exception: " + message, exc.traceback);
    console.log(exc.traceback);
    // catch the error that comes from stale timestamps for files
    if (message.indexOf("ValueError: Requested mtime is") > -1) {
      setTimeout(function () {
        notify("newer datafile found",
          "Newer version of data file(s) found in source...\n\n" +
          "updating template with new file-modified times\n\n" +
          "Please repeat your last request.");
      }, 1);
      app.update_file_mtimes();
    }
    else {
      throw (exc);
    }
  }

  function notify(message, longmessage) {
    // Let's check if the browser supports notifications
    if (!("Notification" in window)) {
      alert(message);
    }

    // Let's check whether notification permissions have already been granted
    else if (Notification.permission === "granted") {
      // If it's okay let's create a notification
      var notification = new Notification(message);
      notification.onclick = function (event) {
        event.preventDefault();
        app_header.show_api_error(longmessage);
      }
      setTimeout(notification.close.bind(notification), 5000);
    }

    // Otherwise, we need to ask the user for permission
    else if (Notification.permission !== 'denied') {
      Notification.requestPermission(function (permission) {
        // If the user accepts, let's create a notification
        if (permission === "granted") {
          var notification = new Notification(message);
          notification.onclick = function (event) {
            event.preventDefault();
            app_header.show_api_error(longmessage);
          }
          setTimeout(notification.close.bind(notification), 5000);
        }
      });
    }

    // Finally, if the user has denied notifications and you
    // want to be respectful there is no need to bother them any more.
  }

  await list_instruments();
  await list_datasources();
  window.onpopstate();
}
