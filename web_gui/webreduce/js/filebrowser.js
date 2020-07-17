// require(jstree, webreduce.server_api)
'use strict';
const filebrowser = {};
export {filebrowser};
//import {jstree} from './libraries.js';
//import {jquery as $} from './libraries.js';
import {editor} from './editor.js';
import {server_api} from './server_api/api_msgpack.js';
import {Tree} from './libraries.js';
import { makeSourceList } from './ui_components/sourcelist.js';

async function categorizeFiles(files_metadata, datasource, path, target_in) {
  let file_objs = await editor.load_metadata(files_metadata, datasource, path);
  var instrument_id = editor._instrument_id;
  var instrument = editor.instruments[instrument_id];
  var categories = instrument.categories;
  var treedata = file_objs_to_tree(file_objs, categories, datasource);
  const node_list = [];
  const leaf_list = [];
  const parents = {};
  const walkTree = function(nodes, parent) {
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
    instrument.decorators.forEach(function(d) {
      d(node_list, leaf_list, parents, file_objs);
    });
  }
  return treedata;
}

async function reference(files_metadata, datasource, path, target_in) {
  var target = $(target_in).find(".remote-filebrowser");
  var ready;
  if (!target.jstree(true)) {
    target.jstree({
      "plugins": ["sort", "checkbox", "changed"],
      "checkbox" : {
        "three_state": true,
        //"cascade": "down",
        "tie_selection": false,
        "whole_node": false
      },
      "sort": sortAlphaNumeric,
      "core": {"data": treeinfo}
    });
    ready = new Promise(function(resolve, reject) {
      target.on("ready.jstree", async function() {
        if (instrument.decorators) {
            instrument.decorators.forEach(async function(d) {
                await d(target, file_objs);
            });
          }
        resolve();
      });
    });
  }
  else {
    //target.off("refresh.jstree");
    target
      .off("check_node.jstree", handleChecked)
      .off("uncheck_node.jstree", handleChecked);
    ready = new Promise(function(resolve, reject) {
      target.one("refresh.jstree", async function(ev, tree) {
        if (instrument.decorators) {
          instrument.decorators.forEach(async function(d) {
              await d(target, file_objs);
          });
          tree.instance.redraw(true);
        }
        
        resolve();
      });
    });
    target.jstree(true).settings.core.data = treeinfo;
    target.jstree(true).refresh();
  }

  await ready;

  target
    .on("check_node.jstree", handleChecked)
    .on("uncheck_node.jstree", handleChecked);
  target.on("click", "a:not(.jstree-anchor)", function(e) {
    window.open(e.target.href, "_blank");
    e.preventDefault();
    e.stopPropagation();
  });
  target.on("click", "a.jstree-anchor", function(e) {
    if (!(e.target.classList.contains("jstree-checkbox"))) {
      //console.log(e.target, e.target.tagName.toLowerCase());
      target.jstree().toggle_node(e.currentTarget.id);
    }
  });

  target.on("fileinfo.update", function(ev, info) {
    var jstree = target.jstree(true);
    jstree.uncheck_all();
    var keys = Object.keys(jstree._model.data);
    info.value.forEach(function(fi) {
      var matching = keys.filter(function(k) {
        var leaf = jstree._model.data[k];
        var isMatch = ((leaf.li_attr) &&
                        leaf.li_attr.entryname == fi.entries[0] &&
                        leaf.li_attr.filename == fi.path &&
                        leaf.li_attr.mtime == fi.mtime)
        return isMatch;
      });
      // turn off the handler for a moment
      // so it doesn't trigger for every check operation:
      target.off("check_node.jstree", handleChecked);
      jstree.check_node(matching);
      // then turn it back on.
      target.on("check_node.jstree", handleChecked);
    });
    //handleChecked(null, null, true);
  });
  return;
}

// categorizers are callbacks that take an info object and return category string
function file_objs_to_tree(file_objs, categories, datasource) {
  // file_obj should always be a list of entries
  var tree = {id: "root", children: []};
  var branch;
  var categories_obj = {};
  var fm;
  console.log(file_objs);
  
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
    for (var e=0; e<fm.length; e++) {
      var entry = fm[e],
          entryname = entry.entry;
      var parent = "root",
          cobj = categories_obj,
          branch = tree,
          category, id;
      let gen = category_generator(entry);
      
      for (var c=0; c<categories.length - 1; c++) {
        category = gen.next().value;
        id = parent + ":" + category;
        let subindex = branch.children.findIndex(c => (c.id == id));
        if (subindex < 0) {
          // not found... add new branch
          let subbranch = {'id': id, text: category, children: []};
          subindex = branch.children.push(subbranch) - 1;
          branch = subbranch;
        }
        else {
          branch = branch.children[subindex];
        }
        parent = id;
      }
      category = gen.next().value; // last one...
      id = [datasource,p,entryname,entry.mtime].join(':');
      let fileinfo = {"filename": p, "entryname": entryname, "mtime": entry.mtime, "source": datasource};
      let leaf = {id, text: category, attributes: {entry: true, fileinfo}}
      branch.children.push(leaf);
    }
  }
  //out.sort(function(aa, bb) { return sortAlphaNumeric(aa.id, bb.id) });

  // if not empty, push in the root node:
  console.log(categories_obj);
  return tree.children;
}

var add_data_source = function(target_id, source, pathlist) {
  var pathlist = pathlist || [];
  var new_div = $("<div />", {"class": "databrowser", "datasource": source});
  $("#" + target_id).prepend(new_div);
  return server_api.get_file_metadata({source: source, pathlist: pathlist}).then(function(result) {
    return updateFileBrowserPane(new_div[0], source, pathlist, result);
  });
}

filebrowser.getAllTemplateSourcePaths = function(template) {
  // Generate a list of all sources/paths for getting needed info from server
  var template = template || editor._active_template;
  var fsp = {}; // group by source and path
  template.modules.forEach(function(m, i) {
    var def = editor._module_defs[m.module];
    var fileinfo_fields = def.fields.filter(function(f) { return f.datatype == "fileinfo" })
      .map(function(f) {return f.id});
    fileinfo_fields.forEach(function(fname) {
      if (m.config && m.config[fname]) {
        m.config[fname].forEach(function(finfo) {
          var parsepath = finfo.path.match(/(.*)\/([^\/]+)*$/);
          if (parsepath) {
            var path = parsepath[1],
                fname = parsepath[2];
            if (! (finfo.source in fsp)) { fsp[finfo.source] = {} }
            if (! (path in fsp[finfo.source])) { fsp[finfo.source][path] = [] }
            fsp[finfo.source][path].push(fname);
          }
        });
      }
    });
  });
  return fsp;
}

var getCurrentPath = function(target_id) {
  // get the path from a specified path browser element
  var target_id = (target_id == null) ? "body" : target_id;
  var path = "";
  $(target_id).find(".patheditor .pathitem").each(function(i,v) {
    path += $(v).text();
  });
  if (/\/$/.test(path)) {path = path.slice(0,-1)}
  return path;
}

var getDataSource = function(target) {
  return $(target).attr("datasource");
}

function getAllBrowserSourcePaths(nav_div) {
  var nav_div = (nav_div == null) ? "#datasources" : nav_div;
  var sourcepaths = [];
  $(nav_div).find(".databrowser").each(function(i,d) {
    sourcepaths.push({source: getDataSource(d), path: getCurrentPath(d)})
  });
  return sourcepaths
}

function updateHistory(target) {
  // call with id or object for nav pane
  var sourcepaths = getAllBrowserSourcePaths(target);
  var urlstr = "?instrument=" + editor._instrument_id;
  if (sourcepaths.length > 0) {
    urlstr += "&" + sourcepaths.map(function(s) {return "source=" + s.source + "&pathlist=" + s.path}).join("&");
  }
  history.pushState({}, "", urlstr);
}

async function updateFileBrowserPane(target, datasource, pathlist, dirdata) {
  var metadata = dirdata.files_metadata;
  var files = Object.keys(metadata);
  files.sort(function(a,b) { return dirdata.files_metadata[b].mtime - dirdata.files_metadata[a].mtime });

  let ds = makeSourceList([{name: datasource, subdirs: dirdata.subdirs, pathlist}]);
  async function pathChange(new_pathlist, index) {
    let dirdata = await server_api.get_file_metadata({source: datasource, pathlist: new_pathlist});
    let treedata = await categorizeFiles(dirdata.files_metadata, datasource, new_pathlist.join("/"), target);
    let tree_el = ds.$refs.sources[index].$refs.tree;
    ds.$set(ds.datasources, index, {name: datasource, pathlist: new_pathlist, subdirs: dirdata.subdirs})
    await ds.$nextTick();
    let tree = new Tree(tree_el, {
      data: treedata,
      closeDepth: -1,
      itemClickToggle: 'closed'
    });
  }
  ds.$on("pathChange", pathChange)
  
  $(target).empty()
    .append(ds.$el)
    .append("<hr>");

  await pathChange(pathlist, 0)
}

async function handleChecked(d, i, stopPropagation) {
  var instrument_id = editor._instrument_id;
  var loader = editor.instruments[instrument_id].load_file;
  var fileinfo = [];
  var loaded_promise = Promise.resolve();
  $(".remote-filebrowser").each(function() {
    var jstree = $(this).jstree(true);
    if (jstree) {
      var checked_nodes = jstree.get_checked().map(function(s) {return jstree.get_node(s)});
      var entrynodes = checked_nodes.filter(function(n) {
        var li = n.li_attr;
        return (li.filename != null && li.entryname != null && li.source != null && li.mtime != null)
      });
      var new_fileinfo = entrynodes.map(function(leaf) {
        var li = leaf.li_attr;
        return {path: li.filename, source: li.source, mtime: li.mtime, entries: [li.entryname]}
      });
      fileinfo = fileinfo.concat(new_fileinfo);

    }
  });
  if (!stopPropagation) {
    $("div.fields").trigger("fileinfo.update", [fileinfo]);
  }
  let loader_template = loader(fileinfo, null, false, 'plottable');
  let results = await editor.calculate(loader_template, false, false);
  let entries = results.map(function(r,i) {
    var values = r.values || [];
    var fi = fileinfo[i];
    var entry = values.find(function(e) { return e.entry == fi.entries[0] });
    return entry;
  });
  let result = {"values": entries}
  editor._active_plot = editor.show_plots([result]);
}

function sortAlphaNumeric(a,b) {
  let asplit = a.match(/(\d+|[^\d]+)/g);
  let bsplit = b.match(/(\d+|[^\d]+)/g);
  
  function comparePart(c,d) {
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
  for (var i=0; i < na && i < nb; i++) {
    let c = asplit[i];
    let d = bsplit[i];
    if (c === undefined) { 
      return 1;
    }
    else if (d === undefined) { 
      return -1;
    }
    else { 
      var cmp = comparePart(c,d);
      if (cmp != null) { 
        return cmp;
      }
    }
  }
  // only get here if all checks return equality.
  return 0
}

filebrowser.updateFileBrowserPane = updateFileBrowserPane;
filebrowser.handleChecked = handleChecked;
filebrowser.getCurrentPath = getCurrentPath;
filebrowser.addDataSource = add_data_source;
filebrowser.getAllBrowserSourcePaths = getAllBrowserSourcePaths;

