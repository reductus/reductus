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
        vars.push(hash[0]);
        vars[hash[0]] = hash[1];
      }
      return vars;
    }

    webreduce.callbacks = {};
    webreduce.callbacks.resize_center = function() {};
    

    window.onpopstate = function(e) {
      // called by load on Safari with null state, so be sure to skip it.
      //if (e.state) {
      var start_path = $.extend(true, [], data_path),
        url_vars = getUrlVars();
      if (url_vars.pathlist && url_vars.pathlist.length) {
        start_path = url_vars.pathlist.split("+");
      }
      webreduce.addDataSource("navigation", "ncnr", start_path);
    }

    

    window.onload = function() {
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
		  
      webreduce.layout = layout;
      webreduce.download = (function () {
        var a = document.createElement("a");
        document.body.appendChild(a);
        a.style = "display: none";
        a.id = "savedata";
        return function (data, fileName) {
          var blob = new Blob([data], {type: "text/plain"}),
            url = window.URL.createObjectURL(blob);
          a.href = url;
          a.download = fileName;
          //window.open(url, '_blank', fileName);
          a.click();
          setTimeout(function() { window.URL.revokeObjectURL(url) }, 1000);
        };
      }());
      
      var upload_dialog = $("#upload_template").dialog({autoOpen: false});
      
      ////////////////////////////////////////////////////////////////////
      // Make a menu
      ////////////////////////////////////////////////////////////////////
      $("#main_menu").append($("<li />", {id: "file_menu", text: "File"})
        .append($("<ul />")
          .append($("<li />", {text: "Download template"})
            .on("click", function() {
              $("#main_menu").hide();
              var filename = prompt("Save template as:", "template.json");
              if (filename == null) {return} // cancelled
              webreduce.download(JSON.stringify(webreduce.editor._active_template, null, 2), filename);
            })
          )
          .append($("<li />", {text: "Upload template"})
            .on("click", function() {$("#main_menu").hide(); upload_dialog.dialog("open")})
          )
        )).menu();
      $("#show_main_menu").on("click", function() {$("#main_menu").toggle()});
   
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
      webreduce.editor.create_instance("bottom_panel");
      webreduce.editor.load_instrument(current_instrument)
        .then(function(instrument_def) { webreduce.editor.load_template(instrument_def.templates[0]); });
      
      webreduce.update_file_mtimes = function(template) {
        var template = template || webreduce.editor._active_template;
        var fsp = {}; // group by source and path for retrieval of info from server
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
        
        // now step through the list of sources and paths and get the mtimes from the server:
        var times_promise = new Promise(function(resolve, reject) {resolve(null)});
        var updated_times = {};
        for (var source in fsp) {
          updated_times[source] = {};
          for (var path in fsp[source]) {
            times_promise = times_promise.then(function() {
              return webreduce.server_api.get_file_metadata(source, path.split("/")).then(function(r) {
                for (var fn in r.files_metadata) {
                  updated_times[source][path + "/" + fn] = r.files_metadata[fn].mtime;
                }
              });
            })
          }
        }
        
        // then step through all the modules again and update the mtimes from the new list
        times_promise.then(function() {
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
        // catch the error that comes from stale timestamps for files
        if (exc.result.error.message.indexOf("ValueError: Requested mtime is") > -1) {
          setTimeout(function() { 
            alert("Newer version of data file(s) found in source...\n\n" + 
                  "updating template with new file-modified times\n\n" + 
                  "Please repeat your last request."); 
          }, 1);
          webreduce.update_file_mtimes();
        }
        else {
          throw(exc);
        }
      }
      window.onpopstate();
  }

})();
