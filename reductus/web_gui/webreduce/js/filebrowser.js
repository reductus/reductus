// require(jstree, webreduce.server_api)
'use strict';
const filebrowser = {};
export { filebrowser };
import { editor } from './editor.js';
import { server_api } from './server_api/api_msgpack.js';
//import { makeSourceList } from './ui_components/sourcelist.js';
import { Vue } from './libraries.js';
import { FilePanel } from './ui_components/file_panel.js';
import { fieldUI } from './ui_components/fields_panel.js';

filebrowser.datasources = [];

async function categorizeFiles(files_metadata, datasource, path) {
  let file_objs = await editor.load_metadata(files_metadata, datasource, path);
  var instrument_id = editor._instrument_id;
  var instrument = editor.instruments[instrument_id];
  var categories = instrument.categories;
  var treedata = file_objs_to_tree(file_objs, categories, datasource);
  const node_list = [];
  const leaf_list = [];
  const parents = {};
  const walkTree = function (nodes, parent, do_sort = true) {
    if (do_sort) {
      nodes.sort(function (aa, bb) { return sortAlphaNumeric(aa.id, bb.id) });
    }
    nodes.forEach(node => {
      node_list.push(node);
      if (parent) parents[node.id] = parent;
      if (node.children && node.children.length) {
        walkTree(node.children, node);
      }
      else {
        leaf_list.push(node);
      }
    });
  };
  walkTree(treedata);
  if (instrument.decorators) {
    instrument.decorators.forEach(function (d) {
      d(node_list, leaf_list, parents, file_objs);
    });
  }
  return treedata;
}

// categorizers are callbacks that take an info object and return category string
function file_objs_to_tree(file_objs, categories, datasource) {
  // file_obj should always be a list of entries
  var tree = { id: "root", children: [] };
  var branch;
  var categories_obj = {};
  var fm;

  function* category_generator(entry) {
    var index = 0;
    for (var category_def of categories) {
      yield category_def.map(
        keylist => keylist.reduce((info, key) => info[key], entry)
      ).join(':');
    }
  }

  for (var p in file_objs) {
    //if (!p) { continue }
    fm = file_objs[p].values;
    for (var e = 0; e < fm.length; e++) {
      var entry = fm[e],
        entryname = entry.entry;
      var parent = "root",
        cobj = categories_obj,
        branch = tree,
        category, id;
      let gen = category_generator(entry);

      for (var c = 0; c < categories.length - 1; c++) {
        category = gen.next().value;
        id = parent + ":" + category;
        let subindex = branch.children.findIndex(c => (c.id == id));
        if (subindex < 0) {
          // not found... add new branch
          let subbranch = { 'id': id, text: category, metadata: {}, attributes: {}, children: [] };
          subindex = branch.children.push(subbranch) - 1;
          branch = subbranch;
        }
        else {
          branch = branch.children[subindex];
        }
        parent = id;
      }
      category = gen.next().value; // last one...
      id = JSON.stringify([datasource, p, entryname, entry.mtime]);
      let fileinfo = { "filename": p, "entryname": entryname, "mtime": entry.mtime, "source": datasource };
      let leaf = { id, text: category, metadata: { fileinfo }, attributes: { entry: true } }
      branch.children.push(leaf);
    }
  }
  //out.sort(function(aa, bb) { return sortAlphaNumeric(aa.id, bb.id) });

  return tree.children;
}

filebrowser.addDataSource = async function (source, pathlist) {
  let dirdata = await server_api.get_file_metadata({ source, pathlist });
  let treedata = await categorizeFiles(dirdata.files_metadata, source, pathlist.join("/"));
  filebrowser.datasources.unshift({ name: source, pathlist, treedata, subdirs: dirdata.subdirs });
  //filebrowser.instance.pathChange(source, pathlist, 0);
}

filebrowser.getAllTemplateSourcePaths = function (template) {
  // Generate a list of all sources/paths for getting needed info from server
  var template = template || editor._active_template;
  var fsp = {}; // group by source and path
  template.modules.forEach(function (m, i) {
    var def = editor._module_defs[m.module];
    var fileinfo_fields = def.fields.filter(function (f) { return f.datatype == "fileinfo" })
      .map(function (f) { return f.id });
    fileinfo_fields.forEach(function (fname) {
      if (m.config && m.config[fname]) {
        m.config[fname].forEach(function (finfo) {
          var parsepath = finfo.path.match(/(.*)\/([^\/]+)*$/);
          if (parsepath) {
            var path = parsepath[1],
              fname = parsepath[2];
            if (!(finfo.source in fsp)) { fsp[finfo.source] = {} }
            if (!(path in fsp[finfo.source])) { fsp[finfo.source][path] = [] }
            fsp[finfo.source][path].push(fname);
          }
        });
      }
    });
  });
  return fsp;
}


function getAllBrowserSourcePaths() {
  return filebrowser.datasources.map(d => ({ source: d.name, path: d.pathlist.join("/") }));
}

function updateHistory(target) {
  // call with id or object for nav pane
  var sourcepaths = getAllBrowserSourcePaths(target);
  var urlstr = "?instrument=" + editor._instrument_id;
  if (sourcepaths.length > 0) {
    urlstr += "&" + sourcepaths.map(function (s) { return "source=" + s.source + "&pathlist=" + s.path }).join("&");
  }
  history.pushState({}, "", urlstr);
}

filebrowser.create_instance = function (target_id) {
  let target = document.getElementById(target_id);
  const FilePanelClass = Vue.extend(FilePanel);
  filebrowser.instance = new FilePanelClass({
    data: () => ({
      datasources: filebrowser.datasources
    }),
    methods: {
      handleChecked,
      async pathChange(source, pathlist, index) {
        let dirdata = await server_api.get_file_metadata({ source, pathlist });
        let subdirs = [...dirdata.subdirs];
        subdirs.sort(sortAlphaNumeric).reverse();
        let treedata = await categorizeFiles(dirdata.files_metadata, source, pathlist.join("/"));
        this.$set(this.datasources, index, { name: source, pathlist, subdirs, treedata })
      },
      setChecked(values) {
        this.$refs.sourcelist.set_checked(values);
      }
    }

  }).$mount(target);
}

filebrowser.refreshAll = function () {
  this.instance.refreshAll();
}

filebrowser.fileinfoUpdate = function (info, update_plots = false) {
  let keys = info.map(fi => (
    JSON.stringify([fi.source, fi.path, fi.entries[0], fi.mtime])
  ));
  this.instance.setChecked(keys);
  if (update_plots) { handleChecked(keys, true) };
}

async function handleChecked(values, stopPropagation) {
  var instrument_id = editor._instrument_id;
  var loader = editor.instruments[instrument_id].load_file;
  var fileinfo = values.map(v => {
    let f = JSON.parse(v);
    let [source, path, entryname, mtime] = JSON.parse(v);
    return { source, path, mtime, entries: [entryname] }
  })

  if (!stopPropagation) {
    fieldUI.instance.update_fileinfo(fileinfo);
  }

  let loader_template = loader(fileinfo, null, false, 'plottable');
  let results = await editor.calculate(loader_template, false, false);
  let entries = results.map(function (r, i) {
    var values = r.values || [];
    var fi = fileinfo[i];
    var entry = values.find(function (e) { return e.entry == fi.entries[0] });
    return entry;
  });
  let result = { "values": entries }
  editor._active_plot = editor.show_plots([result]);
}

function sortAlphaNumeric(a, b) {
  let asplit = a.match(/(\d+|[^\d]+)/g);
  let bsplit = b.match(/(\d+|[^\d]+)/g);

  function comparePart(c, d) {
    if (c == d) return null;
    let c_isnum = c.match(/^\d+$/);
    let d_isnum = d.match(/^\d+$/);
    if (c_isnum && d_isnum) {
      let ci = parseInt(c, 10);
      let di = parseInt(d, 10);
      if (ci == di) {
        return (c > d) ? 1 : -1;
      } else {
        return (ci > di) ? 1 : -1;
      }
    } else {
      return (c > d) ? 1 : -1;
    }
  }

  var na = asplit.length;
  var nb = bsplit.length;
  for (var i = 0; i < na && i < nb; i++) {
    let c = asplit[i];
    let d = bsplit[i];
    if (c === undefined) {
      return 1;
    }
    else if (d === undefined) {
      return -1;
    }
    else {
      var cmp = comparePart(c, d);
      if (cmp != null) {
        return cmp;
      }
    }
  }
  // only get here if all checks return equality.
  return 0
}

//filebrowser.updateFileBrowserPane = updateFileBrowserPane;
filebrowser.handleChecked = handleChecked;
filebrowser.getAllBrowserSourcePaths = getAllBrowserSourcePaths;