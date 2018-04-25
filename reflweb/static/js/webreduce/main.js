webreduce = window.webreduce || {};
webreduce.instruments = webreduce.instruments || {};

(function webreduction() {
   //"use strict";
   // add a comment

  active_reduction = {
    "config": {},
    "template": {}
  }
  current_instrument = "ncnr.refl";

  var NEXUS_ZIP_REGEXP = /\.nxz\.[^\.\/]+$/
  var dirHelper = "listftpfiles.php";
  var data_path = ["ncnrdata"];
  var statusline_log = function(message) {
    var statusline = $("#statusline");
    if (statusline && statusline.html) {
      statusline.html(message);
    }
  }

  webreduce.statusline_log = statusline_log;

  function getUrlVars() {
    var vars = [], hash;
    var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
    for(var i = 0; i < hashes.length; i++) {
      hash = hashes[i].split('=');
      vars.push(hash);
    }
    return vars;
  }

  webreduce.callbacks = {};
  webreduce.callbacks.resize_center = function() {};
  
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

  window.onpopstate = function(e) {
    // called by load on Safari with null state, so be sure to skip it.
    //if (e.state) {
    var datasources = webreduce._datasources || {},
        url_vars = getUrlVars(),
        source = (datasources[0] || {}).name,
        start_path = "";
        
    url_vars.forEach(function(v, i) {
      if (v[0] == 'pathlist' && v[1] && v[1].length) {
        start_path = v[1];
        var pathlist = start_path.split("/");
        webreduce.addDataSource("navigation", source, pathlist);
      }
      else if (v[0] == 'source' && v[1]) {
        source = v[1];
      }
      else if (v[0] == 'instrument' && v[1]) {
        current_instrument = v[1];
        webreduce.editor.switch_instrument(current_instrument);
      }
    })
    
    webreduce.editor.load_stashes();
    
    if (start_path == "") {
      // no data sources added - add the default
      var datasource = datasources.find(function(d) {return d.name == source});
      if (datasource && 'start_path' in datasource) {
        start_path = datasource['start_path'];
      }
      var pathlist = start_path.split("/");
      webreduce.addDataSource("navigation", source, pathlist);
    }
  }

    

  window.onload = function() {
    zip.workerScriptsPath = "js/";
    zip.useWebWorkers = true;
    webreduce.server_api.__init__().then(function(api) {
      var layout = $('body').layout({
           west__size:          350
        ,  east__size:          300
        ,  south__size:         200
          // RESIZE Accordion widget when panes resize
        ,  west__onresize:	    $.layout.callbacks.resizePaneAccordions
        ,  east__onresize:	    $.layout.callbacks.resizePaneAccordions
        ,  south__onresize:     $.layout.callbacks.resizePaneAccordions
        ,  center__onresize:    function() {webreduce.callbacks.resize_center()}
      });

      layout.toggle('east');
      layout.allowOverflow('north');
      //$("#menu").menu({width: '200px;', position: {my: "left top", at: "left+15 bottom"}});
      $(".ui-layout-west")
				.tabs()

	  
      webreduce.layout = layout;
      webreduce.download = (function () {
        var a = document.createElement("a");
        document.body.appendChild(a);
        a.style = "display: none";
        a.id = "savedata";
        return function (data, fileName) {
          var blob = (data instanceof Blob) ? data : new Blob([data], {type: "text/plain"});
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
            setTimeout(function() { window.URL.revokeObjectURL(url) }, 1000);
          }
          // cleanup: this seems to break things!
          //document.body.removeChild(a);
        };
      }());
      
      var api_exception_dialog = $("div#api_exception").dialog({autoOpen: false, width: 600});
      var upload_dialog = $("#upload_template").dialog({autoOpen: false, width: 400});
      var reload_exported_dialog = $("#reload_exported").dialog({autoOpen: false, width: 400});
      var export_data = $("#export_data").dialog({autoOpen: false, width: 400});
      var categories_editor = $("#categories_editor").dialog({autoOpen: false, width: 600});
      
      ////////////////////////////////////////////////////////////////////
      // Make a menu
      ////////////////////////////////////////////////////////////////////
      $("#main_menu")
        .append($("<li />", {id: "file_menu"})
          .append($("<div />", {text: "Template"}), $("<ul />")
            .append($("<li><div>New</div></li>")
              .on("click", function() {
                hide_menu();
                var empty_template = {modules: [], wires: []};
                webreduce.editor.edit_template(empty_template)})
            )
            .append($("<li><div>Edit</div></li>")
              .on("click", function() {hide_menu(); webreduce.editor.edit_template()})
            )
            .append($("<li><div>Download</div></ul>")
              .on("click", function() {
                hide_menu();
                var filename = prompt("Save template as:", "template.json");
                if (filename == null) {return} // cancelled
                webreduce.download(JSON.stringify(webreduce.editor._active_template, null, 2), filename);
              })
            )
            .append($("<li><div>Upload</div></li>")
              .on("click", function() {hide_menu(); upload_dialog.dialog("open")})
            )
            .append($("<li />").append($("<div />")
              .append($("<label />", {text: "Auto-accept changes"})
                .append($("<input />", {type: "checkbox", id: "auto_accept_changes", checked: true}))
                .on("change", function() {hide_menu();})
              )
            ))
            .append($("<li />", {id: "predefined_templates"})
              .append($("<div>Predefined</div>"), $("<ul />"))
              .on("click", "ul li", function(ev) {
                // delegated click handler, so it can get events on elements not added yet
                // (added during instrument_load)
                  hide_menu();
                  var template_id = $(this).text();
                  var instrument_id = webreduce.editor._instrument_id;
                  var template_copy = jQuery.extend(true, {}, webreduce.editor._instrument_def.templates[template_id]);
                  webreduce.editor.load_template(template_copy, null, null, instrument_id);
                  if (localStorage && localStorage.setItem) {
                    var lookup_id = "webreduce.instruments." + instrument_id + ".last_used_template";
                    localStorage.setItem(lookup_id, template_id);
                  }
                })
            )  
          ))
        .append($("<li />", {id: "data_menu"})
          .append($("<div>Data</div>"), $("<ul />")
            .append($("<li><div>Stash</div></ul>")
              .on("click", function() {hide_menu(); webreduce.editor.stash_data()})
            )
            .append($("<li><div>Edit Categories</div></li>")
              .on("click", function() {hide_menu(); webreduce.editor.edit_categories()})
            )
            .append($("<li><div>Export</div></ul>")
              .on("click", function() {hide_menu(); webreduce.editor.export_data()})
            )
            .append($("<li><div>Reload Exported</div></ul>")
              .on("click", function() {hide_menu(); reload_exported_dialog.dialog("open")})
            )
            .append($("<li />").append($("<div />")
              .append($("<label />", {text: "Auto-reload mtimes"})
                .append($("<input />", {type: "checkbox", id: "auto_reload_mtimes", checked: true}))
                .on("change", function() {hide_menu();})
              )
            ))
            .append($("<li />").append($("<div />")
              .append($("<label />", {text: "Cache calculations"})
                .append($("<input />", {type: "checkbox", id: "cache_calculations", checked: true}))
                .on("change", function() {hide_menu();})
              )
            ))
            .append($("<li><div>Clear Cache</div></li>")
              .on("click", function() {hide_menu(); webreduce.editor.clear_cache()})
            )
            .append($("<li />", {id: "data_menu_sources"})//, text: "Add source"})
              .append($("<div>Add source</div>"), $("<ul />"))
            )
          )
        )
        .append($("<li />", {id: "instrument_menu"})// , text: "Instrument"})
          .append($("<div>Instrument</div>"), $("<ul />"))
          .on("click", "ul li", function(ev) {
            // delegated click handler, so it can get events on elements not added yet
            // (added during startup)
              hide_menu();
              webreduce.editor.switch_instrument($(this).text());
            })
          )
        .menu();// .unbind('mouseenter mouseleave');
      
      
      
      function hide_menu() {
        $("#main_menu").menu("collapseAll", null, true).hide();
        $("body").off("click.not-menu");
        return false;
      }

      $("#show_main_menu").on("click", function(ev) {
        if ($("#main_menu").is(":visible")) {
          hide_menu();
        } else {
          $("#main_menu").menu("collapseAll", null, true).show();
          $("body").on("click.not-menu", function(ev) {
            if (!$(ev.target).is("#main_menu_div *")) {
              hide_menu();
            }
          });
        }
        //$("#main_menu").toggle()
      });
   
      $("input#template_file").change(function() {
        var file = this.files[0]; // only one file allowed
        datafilename = file.name;
        this.value = "";
        upload_dialog.dialog("close");
        var reader = new FileReader();
        reader.onload = function(e) {
            //console.log(this.result);
            var template_def = JSON.parse(this.result);
            webreduce.editor.load_template(template_def);
        }
        reader.readAsText(file);
      });
      $("input#exported_file").change(function() {
        var file = this.files[0]; // only one file allowed
        datafilename = file.name;
        this.value = "";
        reload_exported_dialog.dialog("close");
        var reader = new FileReader();
        reader.onload = function(e) {
            //console.log(this.result);
            var first_line = this.result.slice(0, this.result.indexOf('\n'));
            first_line = '{' + first_line.replace(/^#/, '') + '}';
            var template_header = JSON.parse(first_line),
                template_data = template_header.template_data,
                template = template_data.template,
                node = template_data.node,
                terminal = template_data.terminal,
                instrument_id = template_data.instrument_id;
                
            webreduce.editor.load_template(template, node, terminal, instrument_id);
        }
        reader.readAsText(file);
      });
      webreduce.editor.create_instance("bottom_panel");
      
      var list_datasources = webreduce.server_api.list_datasources()
        .then(function(datasources) {
          webreduce._datasources = datasources; // should be a list now.
          datasources.forEach(function(dsource, i){
            var pathlist = (dsource.start_path || "").split("/");
            $("#main_menu #data_menu_sources ul").append($("<li />").append($("<div />", {
              text: dsource.name,
              start_path: dsource.start_path || "",
              click: function() {
                hide_menu();
                webreduce.addDataSource("navigation", dsource.name, pathlist);
              }
            })));
            $("#main_menu").menu("refresh");
          });
          return datasources[0].name;
        });
        
      var list_instruments = webreduce.server_api.list_instruments()
        .then(function(instruments) {
          instruments.forEach(function(d, i){
            $("#main_menu #instrument_menu ul").append($("<li />").append($("<div />", {text: d})));
              $("#main_menu").menu("refresh");
          });
          return instruments[0];
        });
      
      webreduce.update_file_mtimes = function(template) {
        var template = template || webreduce.editor._active_template;
        // First, generate a list of all sources/paths for getting needed info from server
        var fsp = webreduce.getAllTemplateSourcePaths(template);
        
        // now step through the list of sources and paths and get the mtimes from the server:
        var times_promise = new Promise(function(resolve, reject) {resolve(null)});
        var updated_times = {};
        var get_updated = function(source, path) {
          return function() {
            return webreduce.server_api.get_file_metadata({source: source, pathlist: path.split("/")}).then(function(r) {
              for (var fn in r.files_metadata) {
                updated_times[source][path + "/" + fn] = r.files_metadata[fn].mtime;
              }
            });
          }
        }
        for (var source in fsp) {
          updated_times[source] = {};
          for (var path in fsp[source]) {
            times_promise = times_promise.then(get_updated(source, path));
          }
        }
        
        // then step through all the modules again and update the mtimes from the new list
        times_promise = times_promise.then(function() {
          template.modules.forEach(function(m, i) {
            var def = webreduce.editor._module_defs[m.module];
            var fileinfo_fields = def.fields.filter(function(f) { return f.datatype == "fileinfo" })
              .map(function(f) {return f.id});
            fileinfo_fields.forEach(function(fname) {
              if (m.config && m.config[fname]) {
                m.config[fname].forEach(function(finfo) {
                  var new_mtime = updated_times[finfo.source][finfo.path];
                  if (finfo.mtime != new_mtime) {
                    console.log(finfo.path + " old mtime=" + finfo.mtime + ", new mtime=" + new_mtime);
                  }
                  finfo.mtime = new_mtime;
                });
              }
            });
          });
        })
        return times_promise;
      }
      
      webreduce.api_exception_handler = function(exc) {
        console.log("api exception: ", exc);
        var message = exc.exception || "no error message";
        notify("exception: " + message, exc.traceback);
        console.log(exc.traceback);
        // catch the error that comes from stale timestamps for files
        if (message.indexOf("ValueError: Requested mtime is") > -1) {
          setTimeout(function() { 
            notify ("newer datafile found", 
                  "Newer version of data file(s) found in source...\n\n" + 
                  "updating template with new file-modified times\n\n" + 
                  "Please repeat your last request."); 
          }, 1);
          webreduce.update_file_mtimes();
        }
        else {
          throw(exc);
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
          notification.onclick = function(event) {
            event.preventDefault();
            var dialog_div = $("div#api_exception");
            dialog_div.find("pre").text(longmessage);
            dialog_div.dialog("open")
          }
          setTimeout(notification.close.bind(notification), 5000);
        }

        // Otherwise, we need to ask the user for permission
        else if (Notification.permission !== 'denied') {
          Notification.requestPermission(function (permission) {
            // If the user accepts, let's create a notification
            if (permission === "granted") {
              var notification = new Notification(message);
              notification.onclick = function(event) {
                event.preventDefault();
                var dialog_div = $("div#api_exception");
                dialog_div.find("pre").text(longmessage);
                dialog_div.dialog("open")
              }
              setTimeout(notification.close.bind(notification), 5000);
            }
          });
        }

        // Finally, if the user has denied notifications and you 
        // want to be respectful there is no need to bother them any more.
      }

      Promise.all([list_instruments, list_datasources]).then(function(results) {
        var instr = results[0],
            datasource = results[1];
        webreduce.editor.switch_instrument(instr)
          .then(function() { window.onpopstate() })
          .catch(function(e) { console.log(e) });
      });
    });
  }

})();
