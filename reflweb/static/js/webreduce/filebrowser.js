// require(jstree, webreduce.server_api)

(function () {
  var NEXUS_ZIP_REGEXP = /\.nxz\.[^\.\/]+$/
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
    webreduce.editor._file_objs = webreduce.editor._file_objs || {};
    webreduce.editor._file_objs[path] = file_objs;
    var datafiles = files.filter(function(x) {return (
      NEXUS_ZIP_REGEXP.test(x) &&
      (/^(fp_)/.test(x) == false) &&
      (/^rapidscan/.test(x) == false) &&
      (/^scripted_findpeak/.test(x) == false)
      )});
    var loader = webreduce.instruments[instrument_id].load_file;
    var numloaded = 0;
    var numdatafiles = datafiles.length;
    
    if (PARALLEL_LOAD) {
      ////////////////////////////////////////////////////////////////////////////
      // Sends a flotilla of rpc requests to the server
      ////////////////////////////////////////////////////////////////////////////
      datafiles.forEach(function(j, i) {
        load_promises.push(
          loader(datasource, path + "/" + j, files_metadata[j].mtime, file_objs)
            .then(function(r) {webreduce.statusline_log("loaded " + (++numloaded) + " of " + numdatafiles + ": "+ j); return r},
                  function(e) {console.log('failed to load: ', j, e)})
          );
      });
      var p = Promise.all(load_promises).then(function(results) {
        var categorizers = webreduce.instruments[instrument_id].categorizers;
        var treeinfo = file_objs_to_tree(file_objs, categorizers);
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
          "core": {"data": treeinfo}
        });
        return target
      });
    }
    else {
      ////////////////////////////////////////////////////////////////////////////
      // Sends rpc requests one after the other to the server
      ////////////////////////////////////////////////////////////////////////////
      var p = new Promise(function(resolve, reject) {resolve()}),
          results = [];
      datafiles.forEach(function(j, i) {
        p = p.then(function() {
          return loader(datasource, path + "/" + j, files_metadata[j].mtime, file_objs)
            .then(function(r) {webreduce.statusline_log("loaded " + (++numloaded) + " of " + numdatafiles + ": "+ j); results.push(r); return r},
                  function(e) {console.log('failed to load: ', j, e)})
          });
      });
      p = p.then(function() {
        var categorizers = webreduce.instruments[instrument_id].categorizers;
        var treeinfo = file_objs_to_tree(file_objs, categorizers);
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
          "core": {"data": treeinfo}
        });
        return target
      });
    }

    p.then(function(target) {
      target.on("ready.jstree", function() {
        if (webreduce.instruments[instrument_id].decorators) {
            webreduce.instruments[instrument_id].decorators.forEach(function(d) {
                d(target);
            });
          }
      });

      target
        .on("check_node.jstree", handleChecked)
        .on("uncheck_node.jstree", handleChecked);
      target.on("click", "a", function(e) {
        if (!(e.target.classList.contains("jstree-checkbox"))) {
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
        handleChecked(null, null, true);
      });
    });
  }

  // categorizers are callbacks that take an info object and return category string
  function file_objs_to_tree(file_objs, categorizers) {
    // file_obj should always be a list of entries
    var out = [], categories_obj = {}, fm;

    //var out = [], categories_obj = {}, file_obj;
    for (var p in file_objs) {
      fm = file_objs[p].values;
      for (var e=0; e<fm.length; e++) {
        var entry = fm[e],
            entryname = entry.entry;
        var parent = "root",
            cobj = categories_obj,
            category, id;
        for (var c=0; c<categorizers.length; c++) {
          category = categorizers[c](entry);
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
        leaf['li_attr'] = {"filename": p, "entryname": entryname, "mtime": entry.mtime};
      }
    }
    // if not empty, push in the root node:
    if (out.length > 0) { out.push({'id': "root", 'parent': "#", 'text': "", 'state': {'opened': true}}); }
    return out
  }

  var add_data_source = function(target_id, source, path) {
    var new_div = $("<div />", {"class": "databrowser", "datasource": source});
    $("#" + target_id).append(new_div);
    webreduce.server_api.get_file_metadata(source, path).then(function(result) {
      webreduce.updateFileBrowserPane(new_div[0], source, path)(result);
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
  /*
  webreduce.collate_sourcepaths = function(template) {
    var sourcepaths = d3.set();
    template.modules.forEach(function(m) {
      var module_def = webreduce.editor._module_defs[m.module];
      var file_fields = module_def.fields.filter(function(f) {return f.datatype == 'fileinfo'});
      file_fields.forEach(function(ff) {
        if (m.config && ff.id in m.config) {
          var fileinfos = m.config[ff.id];
          if (fileinfos instanceof Array) {
            fileinfos.forEach(function(fi) {
              var path = fi.path.split("/").slice(0,-1).join("/");
              sourcepaths.add(path);
            });
          }
        }
      });
    });
    return sourcepaths;
  }
  */
  /*
  function finfo_to_tree(finfo, path, categorizers){
      var out = [], sample_names = {};
      console.log(Object.keys(finfo));
      for (var fn in finfo) {
        var fn_info = finfo[fn];
        var short_fn = fn.split("/").slice(-1)[0];
        for (var entry in fn_info) {
          var info = fn_info[entry];
          var samplename = info.samplename,
              scantype = info.scantype || "unknown";
          if (!info.samplename) {
            samplename = short_fn.split(".").slice(0)[0];
          }
          sample_names[samplename] = sample_names[samplename] || {};
          sample_names[samplename][scantype] = sample_names[samplename][scantype] || {};
          // min_x and max_x for a file are grabbed from the first entry that pops up:
          sample_names[samplename][scantype][short_fn] = sample_names[samplename][scantype][short_fn] || {min_x: info.min_x, max_x: info.max_x};
          out.push({
            "id": short_fn+":"+entry,
            "parent": short_fn,
            //"text": fn + ":" + entry,
            "text": entry,
            "icon": false,
            "li_attr": {"path": path, "min_x": info.min_x, "max_x": info.max_x}
          });
        }
      }
      for (var sn in sample_names) {
        out.push({"id": sn, "parent": "#", "text": sn});
        var sample_obj = sample_names[sn];
        for (var t in sample_obj) {
          var type_obj = sample_obj[t];
          var global_min_x = Infinity,
              global_max_x = -Infinity;
          for (var fn in type_obj) {
            // once through to get max and min...
            var f_obj = type_obj[fn];
            global_min_x = Math.min(f_obj.min_x, global_min_x);
            global_max_x = Math.max(f_obj.max_x, global_max_x);
          }
          for (var fn in type_obj) {
            // and again to make the range icon.
            var f_obj = type_obj[fn];
            var range_icon = make_range_icon(global_min_x, global_max_x, f_obj.min_x, f_obj.max_x);
            out.push({"id": fn, "parent": sn + ":" + t, "text": "<span>"+fn+"</span>" + range_icon, "icon": false, "li_attr": {"min_x": f_obj.min_x, "max_x": f_obj.max_x, "class": "datafile"}});
          }
          out.push({"id": sn + ":" + t, "parent": sn, "text": t, "li_attr": {"min_x": global_min_x, "max_x": global_max_x}});
        }
      }
      return out;
    }
  */

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
  
  function updateFileBrowserPane(target, datasource, pathlist) {
      function handler(dirdata) {
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
              //history.pushState({}, "", "?pathlist=" + new_pathlist.slice(0, index+1).join("+"));
              webreduce.server_api.get_file_metadata(datasource, new_pathlist.slice(0, index+1))
              .then( function (metadata) {                
                updateFileBrowserPane(target, datasource, new_pathlist.slice(0, index+1))(metadata);
                updateHistory($(target).parent());
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
            //history.pushState({}, "", "?pathlist=" + new_pathlist.join("+"));
            webreduce.server_api.get_file_metadata(datasource, new_pathlist)
              .then( function (metadata) {
                updateFileBrowserPane(target, datasource, new_pathlist)(metadata);
                updateHistory($(target).parent());
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
        categorizeFiles(files, metadata, datasource, pathlist.join("/"), target);

        //$(dirbrowser).selectable({
        //    filter:'td',
        //    stop: handleSelection
        //});
        //$(filebrowser).tablesorter();
      }
      return handler
  }

  function handleChecked(d, i, stopPropagation) {
    var instrument_id = webreduce.editor._instrument_id;
    var xlabel, ylabel
        datas = [],
        options={series: [], axes: {xaxis: {label: "x-axis"}, yaxis: {label: "y-axis"}}},
        fileinfo = [],
        datatype = null,
        entries = [];
    $(".remote-filebrowser").each(function() {
      var jstree = $(this).jstree(true);
      if (jstree) {
        var path = getCurrentPath(this.parentNode);
        var source = getDataSource(this.parentNode);
        var file_objs = webreduce.editor._file_objs[path] || {};
        //var selected_nodes = jstree.get_selected().map(function(s) {return jstree.get_node(s)});
        var checked_nodes = jstree.get_checked().map(function(s) {return jstree.get_node(s)});
        var entrynodes = checked_nodes.filter(function(n) {
          return (n.li_attr.filename != null && n.li_attr.entryname != null)
        });
        var entry_objs = entrynodes.map(function(n) {
          var file_key = n.li_attr.filename,
              entryname = n.li_attr.entryname,
              file_obj = file_objs[file_key],              
              entry_obj = file_obj.values.find(function(r) {return r.entry == entryname}),
              //filename = file_key.split("/").slice(-1).join(""),
              mtime = n.li_attr.mtime;
          fileinfo.push({path: file_key, source: source, mtime: mtime, entries: [entryname]});
          if (datatype == null) { datatype = file_obj.datatype }
          else if (datatype != file_obj.datatype) {
            console.log("warning: datatypes do not match in loaded files"); 
          }
          return entry_obj;
        });
        entries = entries.concat(entry_objs);
        /*
        var new_plotdata = webreduce.instruments[instrument_id].plot(entry_objs);
        options.series = options.series.concat(new_plotdata.series);
        datas = datas.concat(new_plotdata.data);
        if (xlabel != null && new_plotdata.xlabel != xlabel) {
          throw "mismatched x axes in selection: " + String(xlabel) + " and " + String(new_plotdata.xlabel);
        }
        else {
          xlabel = new_plotdata.xlabel;
        }
        if (ylabel != null && new_plotdata.ylabel != ylabel) {
          throw "mismatched y axes in selection: " + String(ylabel) + " and " + String(new_plotdata.ylabel);
        }
        else {
          ylabel = new_plotdata.ylabel;
        }
        */
      }
    });
    if (!stopPropagation) {
      $("div.fields").trigger("fileinfo.update", [fileinfo]);
    }
    var result = {"datatype": datatype, "values": entries}
    webreduce.editor._active_plot = webreduce.editor.show_plots(result);
  }
  webreduce = window.webreduce || {};
  webreduce.updateFileBrowserPane = updateFileBrowserPane;
  webreduce.handleChecked = handleChecked;
  webreduce.getCurrentPath = getCurrentPath;
  webreduce.addDataSource = add_data_source;
  webreduce.getAllBrowserSourcePaths = getAllBrowserSourcePaths;

})();
