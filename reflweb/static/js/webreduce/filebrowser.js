// require(jstree, webreduce.server_api)
'use strict';

(function () {
  var NEXUS_ZIP_REGEXP = /\.nxz\.[^\.\/]+$/
  var ZIP_REGEXP = /\.zip$/
  var BRUKER_REGEXP = /\.ra[ws]$/
  var PARALLEL_LOAD = true;

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

  function categorizeFiles(files, files_metadata, datasource, path, target_in) {
    var instrument_id = webreduce.editor._instrument_id;
    var load_promises = [];
    var fileinfo = {};
    var file_objs = {};
    var datafiles = files.filter(function(x) {return (
      BRUKER_REGEXP.test(x) ||
      ZIP_REGEXP.test(x) ||
      (NEXUS_ZIP_REGEXP.test(x) &&
       (/^(fp_)/.test(x) == false) &&
       (/^rapidscan/.test(x) == false) &&
       (/^scripted_findpeak/.test(x) == false))
      )});
    var loader = webreduce.instruments[instrument_id].load_file;
    var numloaded = 0;
    var numdatafiles = datafiles.length;

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
    var p = loader(load_params, file_objs, false, 'metadata')
      .then(function(results) {
        webreduce.editor._datafiles = results;
        var categories = webreduce.instruments[instrument_id].categories;
        var treeinfo = file_objs_to_tree(file_objs, categories, datasource);
        // add decorators etc to the tree with postprocess:
        var postprocess = webreduce.instruments[instrument_id].postprocess;
        if (postprocess) { postprocess(treeinfo, file_objs) }
        var target = $(target_in).find(".remote-filebrowser");
        var jstree = target.jstree({
          "plugins": ["checkbox", "changed", "sort"],
          "checkbox" : {
            "three_state": true,
            //"cascade": "down",
            "tie_selection": false,
            "whole_node": false
          },
          "sort": sortAlphaNumeric,
          "core": {"data": treeinfo}
        });
        return target
      });

    p.then(function(target) {
      var ready = new Promise(function(resolve, reject) {
        target.on("ready.jstree", function() {
          if (webreduce.instruments[instrument_id].decorators) {
              var dp = Promise.resolve();
              webreduce.instruments[instrument_id].decorators.forEach(function(d) {
                  dp = dp.then(function() { return d(target, file_objs) });
              });
            }
          resolve();
        });
      });

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
      return ready;
    });
    return p;

  }

  // categorizers are callbacks that take an info object and return category string
  function file_objs_to_tree(file_objs, categories, datasource) {
    // file_obj should always be a list of entries
    var out = [], categories_obj = {}, fm;

    //var out = [], categories_obj = {}, file_obj;      
    for (var p in file_objs) {
      //if (!p) { continue }
      fm = file_objs[p].values;
      for (var e=0; e<fm.length; e++) {
        var entry = fm[e],
            entryname = entry.entry;
        var parent = "root",
            cobj = categories_obj,
            category, id;
        for (var c=0; c<categories.length; c++) {
          category = categories[c]
            .map(function(keylist) { 
              return keylist.reduce(function(info, key) { return info[key] }, entry)
            }).join(":");
          id = parent + ":" + category;
          if (!(category in cobj)) {
            cobj[category] = {};
            var leaf = {'id': id, text: category, parent: parent, "icon": false};
            out.push(leaf);
          }
          parent = id;
          cobj = cobj[category]; // walk the tree...
        }
        // modify the last entry to include key of file_obj
        leaf['li_attr'] = {"filename": p, "entryname": entryname, "mtime": entry.mtime, "source": datasource};
      }
    }
    // if not empty, push in the root node:
    if (out.length > 0) { out.push({'id': "root", 'parent': "#", 'text': "", 'state': {'opened': true}}); }
    return out
  }

  var add_data_source = function(target_id, source, pathlist) {
    var pathlist = pathlist || [];
    var new_div = $("<div />", {"class": "databrowser", "datasource": source});
    $("#" + target_id).prepend(new_div);
    return webreduce.server_api.get_file_metadata({source: source, pathlist: pathlist}).then(function(result) {
      return webreduce.updateFileBrowserPane(new_div[0], source, pathlist, result);
    });
  }

  webreduce.getAllTemplateSourcePaths = function(template) {
    // Generate a list of all sources/paths for getting needed info from server
    var template = template || webreduce.editor._active_template;
    var fsp = {}; // group by source and path
    template.modules.forEach(function(m, i) {
      var def = webreduce.editor._module_defs[m.module];
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
    $(target_id).find(".patheditor span").each(function(i,v) {
      path += $(v).text();
    });
    if (/\/$/.test(path)) {path = path.slice(0,-1)}
    return path;
  }

  var getDataSource = function(target) {
    return $(target).attr("datasource");
  }

  function getAllBrowserSourcePaths(nav_div) {
    var nav_div = (nav_div == null) ? "#navigation" : nav_div;
    var sourcepaths = [];
    $(nav_div).find(".databrowser").each(function(i,d) {
      sourcepaths.push({source: getDataSource(d), path: getCurrentPath(d)})
    });
    return sourcepaths
  }

  function updateHistory(target) {
    // call with id or object for nav pane
    var sourcepaths = getAllBrowserSourcePaths(target);
    var urlstr = "?instrument=" + webreduce.editor._instrument_id;
    if (sourcepaths.length > 0) {
      urlstr += "&" + sourcepaths.map(function(s) {return "source=" + s.source + "&pathlist=" + s.path}).join("&");
    }
    history.pushState({}, "", urlstr);
  }

  function updateFileBrowserPane(target, datasource, pathlist, dirdata) {
    var buttons = $("<div />", {class: "buttons"});
    var clear_all = $("<button />", {text: "uncheck all"});
    clear_all.click(function() {$(".remote-filebrowser", target)
      .jstree("uncheck_all"); handleChecked();
    });
    var remove_datasource = $("<button />", {text: "remove"});
    remove_datasource.click(function() { var nav=$(target).parent(); $(target).empty().remove(); updateHistory(nav);});
    buttons
      //.append($("<span />", {class: "ui-icon ui-icon-circle-close"}))
      .append(clear_all)
      .append(remove_datasource)
      .append('<span class="datasource">source: ' + datasource + '</span>');

    var files = dirdata.files,
        metadata = dirdata.files_metadata;
    files.sort(function(a,b) { return dirdata.files_metadata[b].mtime - dirdata.files_metadata[a].mtime });
    // dirdata is {'subdirs': list_of_subdirs, 'files': list_of_files, 'pathlist': list_of_path

    var patheditor = document.createElement('div');
    patheditor.className = 'patheditor';
    var subdiritem, dirlink, new_pathlist;
    if (pathlist.length > 0) {
      var new_pathlist = $.extend(true, [], pathlist);
      $.each(new_pathlist, function(index, pathitem) {
        dirlink = document.createElement('span');
        dirlink.textContent = pathitem + "/";
        dirlink.onclick = function() {
          webreduce.server_api.get_file_metadata({source: datasource, pathlist: new_pathlist.slice(0, index+1)})
          .then( function (metadata) {
            updateFileBrowserPane(target, datasource, new_pathlist.slice(0, index+1), metadata);
            //updateHistory($(target).parent());
          })
        }
        patheditor.appendChild(dirlink);
      });
    }

    var dirbrowser = document.createElement('ul');
    dirbrowser.id = "dirbrowser";
    dirbrowser.setAttribute("style", "margin:0px;");
    dirdata.subdirs.reverse();
    $.each(dirdata.subdirs, function(index, subdir) {
      subdiritem = document.createElement('li');
      subdiritem.classList.add('subdiritem');
      subdiritem.textContent = "(dir) " + subdir;
      var new_pathlist = $.extend(true, [], pathlist);
      new_pathlist.push(subdir);
      subdiritem.onclick = function() {
        webreduce.server_api.get_file_metadata({source: datasource, pathlist: new_pathlist})
          .then( function (metadata) {
            updateFileBrowserPane(target, datasource, new_pathlist, metadata);
            //updateHistory($(target).parent());
          })
      }
      dirbrowser.appendChild(subdiritem);
    });

    var filebrowser = document.createElement('div');
    filebrowser.classList.add("remote-filebrowser");

    $(target).empty()
      .append(buttons)
      .append(patheditor)
      //.append(deadtime_choose)
      .append(dirbrowser)
      .append(filebrowser)
      .append("<hr>");

    // instrument-specific categorizers
    // webreduce.instruments[instrument_id].categorizeFiles(files, metadata, pathlist.join("/"), target_id);
    return categorizeFiles(files, metadata, datasource, pathlist.join("/"), target);
  }

  function handleChecked(d, i, stopPropagation) {
    var instrument_id = webreduce.editor._instrument_id;
    var loader = webreduce.instruments[instrument_id].load_file;
    var xlabel, ylabel,
        datas = [],
        options={series: [], axes: {xaxis: {label: "x-axis"}, yaxis: {label: "y-axis"}}},
        fileinfo = [],
        datatype = null,
        entries = []
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
    loader(fileinfo, null, false, 'plottable').then(function(results) {
      var entries = results.map(function(r,i) {
        var values = r.values || [];
        var fi = fileinfo[i];
        var entry = values.find(function(e) { return e.entry == fi.entries[0] });
        if (datatype == null) { datatype = r.datatype }
        else if (datatype != r.datatype) {
          console.log("warning: datatypes do not match in loaded files");
        }
        return entry;
      });
      var result = {"datatype": datatype, "values": entries}
      webreduce.editor._active_plot = webreduce.editor.show_plots(result);
    });
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

  webreduce = window.webreduce || {};
  webreduce.updateFileBrowserPane = updateFileBrowserPane;
  webreduce.handleChecked = handleChecked;
  webreduce.getCurrentPath = getCurrentPath;
  webreduce.addDataSource = add_data_source;
  webreduce.getAllBrowserSourcePaths = getAllBrowserSourcePaths;

})();
