// require(jstree, webreduce.server_api)

(function () {
  var NEXUS_ZIP_REGEXP = /\.nxz\.[^\.\/]+$/

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

  function categorizeFiles(files, files_metadata, datasource, path, target_in, instrument_id) {
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
    datafiles.forEach(function(j) {
      load_promises.push(loader(datasource, path + "/" + j, files_metadata[j].mtime, file_objs));
    });
    Promise.all(load_promises).then(function(results) {
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
          jstree.check_node(matching);
        });
        handleChecked(null, null, true);
      });
    });
  }

  // categorizers are callbacks that take an info object and return category string
  function file_objs_to_tree(file_objs, categorizers) {
    // file_obj should always be a list of entries
    var out = [], categories_obj = {}, file_obj;

    //var out = [], categories_obj = {}, file_obj;
    for (var p in file_objs) {
      file_obj = file_objs[p];
      for (var e=0; e<file_obj.length; e++) {
        var entry = file_obj[e],
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

  var add_remote_source = function(target_id, source, path) {
    var new_div = $("<div />", {"class": "remote-filebrowser"});
    $("#" + target_id).append(new_div);
    webreduce.server_api.get_file_metadata(source, path).then(function(result) {
      webreduce.updateFileBrowserPane(new_div[0], source, path, current_instrument)(result);
    });
  }

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

  function updateFileBrowserPane(target, datasource, pathlist, instrument_id) {
      function handler(dirdata) {
        var buttons = $("<div />", {class: "buttons"});
        var clear_all = $("<button />", {text: "clear all"});
        clear_all.click(function() {$(target)
          .jstree("uncheck_all"); handleChecked();
        });
        buttons
          .append(clear_all)

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
              history.pushState({}, "", "?pathlist=" + new_pathlist.slice(0, index+1).join("+"));
              webreduce.server_api.get_file_metadata(datasource, new_pathlist.slice(0, index+1))
              .then( function (metadata) {
                 updateFileBrowserPane(target, datasource, new_pathlist.slice(0, index+1), instrument_id)(metadata);
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
            history.pushState({}, "", "?pathlist=" + new_pathlist.join("+"));
            webreduce.server_api.get_file_metadata(datasource, new_pathlist)
              .then( function (metadata) {
                 updateFileBrowserPane(target, datasource, new_pathlist, instrument_id)(metadata);
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
          .append(filebrowser);

        // instrument-specific categorizers
        // webreduce.instruments[instrument_id].categorizeFiles(files, metadata, pathlist.join("/"), target_id);
        categorizeFiles(files, metadata, datasource, pathlist.join("/"), target, instrument_id);

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
    var xcol,
        datas = [],
        options={series: [], axes: {xaxis: {label: "x-axis"}, yaxis: {label: "y-axis"}}},
        fileinfo = [];
    $(".remote-filebrowser").each(function() {
      var jstree = $(this).jstree(true);
      if (jstree) {
        var path = getCurrentPath(this.parentNode);
        var file_objs = webreduce.editor._file_objs[path] || {};
        //var selected_nodes = jstree.get_selected().map(function(s) {return jstree.get_node(s)});
        var checked_nodes = jstree.get_checked().map(function(s) {return jstree.get_node(s)});
        var entrynodes = checked_nodes.filter(function(n) {
          return (n.li_attr.filename != null && n.li_attr.entryname != null)
        });
        var entry_ids = entrynodes.map(function(n) {
          var file_obj_key = n.li_attr.filename,
              entryname = n.li_attr.entryname,
              filename = file_obj_key.split("/").slice(-1).join("");
              mtime = n.li_attr.mtime;
          fileinfo.push({path: file_obj_key, mtime: mtime, entries: [entryname]})
          /*var file_entry = n.li_attr.file_entry,
              file_obj = file_entry.split(":").slice(0,1).join(""),
              filename = file_obj.split("/").slice(-1).join(""),
              entryname = file_entry.split(":").slice(-1).join("");
          */
          return {file_obj: file_obj_key, filename: filename, entryname: entryname}
        });
        var new_plotdata = webreduce.instruments[instrument_id].plot_files(file_objs, entry_ids);
        options.series = options.series.concat(new_plotdata.series);
        datas = datas.concat(new_plotdata.data);
        if (xcol != null && new_plotdata.xcol != xcol) {
          throw "mismatched x axes in selection: " + String(xcol) + " and " + String(new_plotdata.xcol);
        }
        else {
          xcol = new_plotdata.xcol;
        }
      }
    });
    if (!stopPropagation) {
      $("div.fields").trigger("fileinfo.update", [fileinfo]);
    }
    //options.axes.xaxis.label = "Qz (target)";
    options.legend = {"show": true, "left": 125};
    options.axes.xaxis.label = xcol;
    options.axes.yaxis.label = "counts/monitor";
    options.xtransform = $("#xscale").val();
    options.ytransform = $("#yscale").val();
    var mychart = new xyChart(options);
    d3.selectAll("#plotdiv svg").remove();
    d3.selectAll("#plotdiv").data([datas]).call(mychart);
    d3.selectAll("#xscale, #yscale").on("change", function() {
      var axis = d3.select(this).attr("axis") + "transform",
          transform = this.value;
      mychart[axis](transform);  
    });
      var x0 = 10,
          y0 = 10,
          dx = 135,
          dy = 40;
    mychart.zoomRect(true);
  }
  webreduce = window.webreduce || {};
  webreduce.updateFileBrowserPane = updateFileBrowserPane;
  webreduce.handleChecked = handleChecked;
  webreduce.getCurrentPath = getCurrentPath;
  webreduce.addRemoteSource = add_remote_source;

})();
