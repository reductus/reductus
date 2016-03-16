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
      webreduce.addRemoteSource("navigation", "ncnr", start_path);
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
      //$.post(dirHelper, {'pathlist': $("#remote_path").val().split("/")}, function(r) { categorize_files(r.files)});
      $(".file .menu-items .download").on("click", function() {
        var filename = prompt("Save template as:", "template.json");
        if (filename == null) {return} // cancelled
        webreduce.download(JSON.stringify(webreduce.editor._active_template, null, 2), filename);
      });
      $(".file .menu-items .upload").on("click", function() {
        upload_dialog.dialog("open");
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
            webreduce.editor._instance.data()[0].modules = template_def.modules;
            webreduce.editor._instance.data()[0].wires = template_def.wires;
            webreduce.editor._instance.update(); 
        }
        reader.readAsText(file);
      });
      webreduce.editor.create_instance("bottom_panel");
      webreduce.editor.load_instrument(current_instrument)
        .then(function(instrument_def) { webreduce.editor.load_template(instrument_def.templates[0]); });
        
      window.onpopstate();
  }

})();
