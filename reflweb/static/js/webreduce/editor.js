// require(d3.js, webreduce.server_api, dataflow)
// require(d3, dataflow)

webreduce.editor = webreduce.editor || {};

(function () {
	webreduce.editor.dispatch = d3.dispatch("accept");

  webreduce.guid = function() {
    var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = Math.random()*16|0,v=c=='x'?r:r&0x3|0x8;
      return v.toString(16);});
    return uuid;
  }

  webreduce.editor._cache = new PouchDB("calculations");

  webreduce.editor.create_instance = function(target_id) {
    // create an instance of the dataflow editor in
    // the html element referenced by target_id
    this._instance = new dataflow.editor();
    this._target_id = target_id;
    this._instance.data([{modules:[],wires: []}]);
    var target = d3.select("#" + target_id);
    target.call(this._instance);
    d3.select("body").on("keydown.accept", null);
    d3.select("body").on("keydown.accept", function() {
      var key = d3.event.key;
      if (key.toLowerCase && key.toLowerCase() == "enter") {
        var accept_fn = d3.select("button.accept.config").on("click");
        if (accept_fn) { accept_fn(); }
        return false
      }
    }) 
  }
  
  webreduce.editor.handle_module_clicked = function(d,i,clicked_elem) {
    // d module data, i is module index, elem is registered to catch event
    //
    // Flow: 
    //  - if the module title is clicked, show configuration and 
    //    data from the first input terminal.
    //  - if input terminal is clicked, show that data and configuration
    //  - if output terminal is clicked, show that data and configuration
    
    var editor = d3.select("#" + webreduce.editor._target_id);
    var elem = this; // this function is called from the context of a select.on   
    var clicked_elem = clicked_elem || d3.event.target;
    var multiple_select = (d3.event && (d3.event.shiftKey || d3.event.ctrlKey));
    var data_to_show;
    
    // clear all the stashed items, since we are plotting from the template again
    d3.selectAll("#stashedlist input.compare").property("checked", false);
    
    if (multiple_select) {
      var active_node = i,
          active_terminal = d3.select(clicked_elem).attr("terminal_id");
      if (!d3.select(clicked_elem).classed("terminal")) {
        console.log("can't select multiple module configs, just inputs and outputs");
        return
      }
      var parent = d3.select(clicked_elem.parentNode);
      parent.classed("selected", !(parent.classed("selected")));
      editor.selectAll("g.module, g.module g.title").classed("selected", false);
      webreduce.layout.close("east");
      var config_target = d3.select(".ui-layout-pane-east");
      config_target.selectAll("div").remove();
      var to_compare = [];
      editor.selectAll("g.module").each(function(dd, ii) {
        d3.select(this).selectAll("g.selected rect.terminal").each(function(ddd,iii) {
          var tid = d3.select(this).attr("terminal_id");
          to_compare.push({"node": ii, "terminal": tid})
        });
      });
      compare_in_template(to_compare, active_template);
    }
    else {
      editor.selectAll(".module .selected").classed("selected", false);
      d3.select(clicked_elem.parentNode).classed("selected", true);
      
      var active_template = webreduce.editor._active_template;
      var active_module = active_template.modules[i];
      var module_def = webreduce.editor._module_defs[active_module.module];
      var fields = module_def.fields || [];
      if (fields.filter(function(d) {return d.datatype == 'fileinfo'}).length == 0) {
          var nav = $("#navigation");
          nav.block({message: null, fadeIn:0, overlayCSS: {opacity: 0.25, cursor: 'not-allowed', height: nav.prop("scrollHeight")}});
      }
      
      if (d3.select(clicked_elem).classed("title")) {
        // then it's the module title clicked - 
        // select the first input terminal to show data from (if any)
        data_to_show = (module_def.inputs[0] || {}).id;  // second part undefined if no inputs
        // also highlight the first input terminal, if it's there:
        d3.select(elem).selectAll("g")
          .filter(function(d) { return d.id == data_to_show })
          .classed("selected", true);
      }
      else {
        // it's a terminal - show the data in it with the configuration
        //var side = d3.select(clicked_elem).classed("input") ? "input" : "output";
        data_to_show = d3.select(clicked_elem).attr("terminal_id");
        // also mark title of module as selected:
        d3.select(elem).select("g.title").classed("selected", true);
      }
      webreduce.editor._active_node = i;
      webreduce.editor._active_terminal = data_to_show;

      webreduce.layout.open("east");
      var config_target = d3.select(".ui-layout-pane-east");
      config_target.selectAll("div").remove();
      var header = config_target
        .append("div")
        .style("display", "block");
      header
        .append("h3")
        .style("margin", "5px")
        .style("display", "inline-block")
        .text(module_def.name);
      header
        .append("button")
        .text("help")
        .on("click", function() {
          var helpwindow = window.open("", "help", "location=0,toolbar=no,menubar=no,scrollbars=yes,resizable=yes,width=960,height=480");
          helpwindow.document.title = "Web reduction help";
          helpwindow.document.write(module_def.description);
          helpwindow.document.close();
          if (helpwindow.MathJax) {
            helpwindow.MathJax.Hub.Queue(["Typeset", helpwindow.MathJax.Hub]);
          }
        });
      
      var buttons_div = config_target.append("div")
        .classed("control-buttons", true)
        .style("position", "absolute")
        .style("bottom", "10px")
      buttons_div.append("button")
        .text("accept")
        .classed("accept config", true)
        .on("click", function() {
          webreduce.editor.accept_parameters(config_target, active_module);
          if (!(d3.select(clicked_elem).classed("output"))) {
            // find the first output and select that one...
            var first_output = module_def.outputs[0].id;
            clicked_elem = d3.select(elem).select('rect.terminal[terminal_id="'+first_output+'"]').node();          
          }
          webreduce.editor.handle_module_clicked.call(elem,d,i,clicked_elem);
        })
      buttons_div.append("button")
        .text("clear")
        .classed("clear config", true)
        .on("click", function() {
          //console.log(config_target, active_module);
          if (active_module.config) { delete active_module.config }
          webreduce.editor.handle_module_clicked.call(elem,d,i,clicked_elem);
        })
        
      $(buttons_div).buttonset();
      
      var terminals_to_calculate = module_def.inputs.map(function(inp) {return inp.id});
      var fields_in = {};
      if (data_to_show != null && terminals_to_calculate.indexOf(data_to_show) < 0) {
        terminals_to_calculate.push(data_to_show);
      }
      var recalc_mtimes = $("#auto_reload_mtimes").prop("checked"),
          params_to_calc = terminals_to_calculate.map(function(terminal_id) {
            return {template: active_template, config: {}, node: i, terminal: terminal_id, return_type: "metadata"}
          })
      webreduce.editor.calculate(params_to_calc, recalc_mtimes)
        .then(function(results) {
        var inputs_map = {};
        var id;
        results.forEach(function(r, ii) {
          id = terminals_to_calculate[ii];
          inputs_map[id] = r;
        })
        return inputs_map
      }).then(function(im) {
        var datasets_in = im[data_to_show];
        var field_inputs = module_def.inputs
          .filter(function(d) {return /\.params$/.test(d.datatype)})
          .map(function(d) {return im[d.id]})
        field_inputs.forEach(function(d) {
          d.values.forEach(function(v) {
            $.extend(true, fields_in, v);
          });
        });
        webreduce.editor.show_plots(datasets_in);
        fields.forEach(function(field) {
          if (webreduce.editor.make_fieldUI[field.datatype]) {
            var value;
            var passthrough = false;
            if (field.id in fields_in) {
              value = fields_in[field.id];
              passthrough = true;
            }
            else if (active_module.config && field.id in active_module.config) {
              value = active_module.config[field.id];
            }
            else {
              // make a copy - if field.default is an object, it will be modified!
              var field_copy =  $.extend(true, {}, field);
              value = field_copy.default;
            }
            var datum = {"id": field.id, "value": value, "passthrough": passthrough};
            var fieldUI = webreduce.editor.make_fieldUI[field.datatype](field, active_template, datum, module_def, config_target, datasets_in);
            if (passthrough) {fieldUI.property("disabled", true)};
          }
        });
      });
    }
  }
  
  function compare_in_template(to_compare, template) {
    var template = template || webreduce.editor._active_template,
        recalc_mtimes = $("#auto_reload_mtimes").prop("checked");
        params_to_calc = to_compare.map(function(a) {
          return {template: template, config: {}, node: a.node, terminal: a.terminal, return_type: "metadata"}
        });
    return webreduce.editor.calculate(params_to_calc, recalc_mtimes)
      .then(function(results) {
        var output;
        if (results.length < 1) { 
          output = {"datatype": "none", "values": []} 
        }
        else { 
          output = results[0];
          for (var i=1; i<results.length; i++) {
            if (results[i].datatype == output.datatype) {
              output.values = output.values.concat(results[i].values);
            }
          }
        }
        webreduce.editor.show_plots(output);
      });
  }
  
  webreduce.editor.show_plots = function(result) {
    var instrument_id = this._instrument_id;
    var new_plotdata = webreduce.instruments[instrument_id].plot(result);
    var active_plot;
    if (new_plotdata == null) {
      active_plot = null;
      d3.select("#plotdiv").selectAll("svg, div").remove();
      d3.select("#plotdiv").append("div")
        .style("position", "absolute")
        .style("top", "0px")
        .style("text-align", "center")
        .append("h1").html("&#8709;")
    }
    else if (new_plotdata.type == '1d') {
      active_plot = this.show_plots_1d(new_plotdata);
    }
    else if (new_plotdata.type == '2d') {
      active_plot = this.show_plots_2d(new_plotdata);
    }
    else if (new_plotdata.type == 'params') {
      active_ploat = this.show_plots_params(new_plotdata);
    }
    this._active_plot = active_plot;
    return active_plot;
  }
  
  webreduce.editor.show_plots_params = function(data) {
    d3.selectAll("#plotdiv").selectAll("svg, div").remove();
    d3.select("#plotdiv")
      .selectAll(".paramsDisplay")
      .data(data.params).enter()
        .append("div").append("pre")
        .classed("paramsDisplay", true)
        .text(function(d) {return JSON.stringify(d, null, 2)})
    return data
  }
  
  webreduce.editor.show_plots_2d = function(data) {
    var aspect_ratio = null;
    if ((((data.options || {}).fixedAspect || {}).fixAspect || null) == true) {
      aspect_ratio = ((data.options || {}).fixedAspect || {}).aspectRatio || null;
    }
    data.ztransform = $("#zscale").val();
    
    var mychart = new heatChart(data);
    mychart
      //.ztransform((transform == "log")? "log" : "linear")
      //.colormap(cm.get_colormap(current_instr == "NGBSANS" ? "spectral" : "jet"))
      .autoscale(false)
      .aspect_ratio(aspect_ratio)
      .dims(data.dims)
      .xlabel(data.xlabel)
      .ylabel(data.ylabel);
    d3.selectAll("#plotdiv").selectAll("svg, div").remove();
    d3.selectAll("#plotdiv").data(data.z).call(mychart);
    mychart.zoomScroll(true);
    
    // set up plot control buttons and options:
    if (d3.select("#plot_controls").attr("plot_type") != "2d") {
      // then make the controls:
      var plot_controls = d3.select("#plot_controls")
      plot_controls.attr("plot_type", "2d")
      plot_controls.selectAll("select,input,button,label").remove();
      plot_controls.selectAll(".scale-select")
        .data(["zscale"])
        .enter().append("label")
        .classed("scale-select", true)
        .text(function(d) {return d})
        .append("select")
          .attr("id", function(d) {return d})
          .attr("axis", function(d) {return d[0]})
          .on("change", function() {
            var axis = d3.select(this).attr("axis") + "transform",
                transform = this.value;
            webreduce.editor._active_plot[axis](transform);  
          })
          .selectAll("option").data(["linear", "log"])
            .enter().append("option")
            .attr("value", function(d) {return d})
            .text(function(d) {return d})
      plot_controls.selectAll(".show-boxes")
        .data(["grid"])
        .enter().append("label")
        .classed("show-boxes", true)
        .text(function(d) {return d})
        .append("input")
          .attr("id", function(d) {return "show_" + d})
          .attr("type", "checkbox")
          .attr("checked", "checked")
          .on("change", function() {
            mychart[this.id](this.checked);
          });
      
      /*
      plot_controls.selectAll(".show-boxes") // want to show/hide grids in the future...
        .data(["errorbars", "points", "line"])
        .enter().append("label")
        .classed("show-boxes", true)
        .text(function(d) {return d})
        .append("input")
          .attr("id", function(d) {return "show_" + d})
          .attr("type", "checkbox")
          .attr("checked", "checked")
          .on("change", function() {
            var o = mychart.options();
            o[this.id] = this.checked;
            mychart.options(o).update();
          });
       */
          
       plot_controls
        .append("input")
          .attr("type", "button")
          .attr("id", "export_data")
          .attr("value", "export")
          .on("click", webreduce.editor.export_data)
    }

    mychart.autofit();
    return mychart
  }
  
  webreduce.editor.show_plots_1d = function(plotdata) {
    var options = {
      series: [],
      legend: {show: true, left: 150},
      axes: {xaxis: {label: "x-axis"}, yaxis: {label: "y-axis"}}
    };
    jQuery.extend(true, options, plotdata.options);
    if (options.xtransform) {
      $("#xscale").val(options.xtransform);
    } else {
      options.xtransform = $("#xscale").val();
    }
    if (options.ytransform) {
      $("#yscale").val(options.ytransform);
    } else {
      options.ytransform = $("#yscale").val();
    }
    options.show_errorbars = $("#show_errorbars").prop("checked");
    options.show_points = $("#show_points").prop("checked");
    options.show_line = $("#show_line").prop("checked");
    
    // create the 1d chart:
    var mychart = new xyChart(options);
    d3.selectAll("#plotdiv").selectAll("svg, div").remove();
    d3.selectAll("#plotdiv").data([plotdata.data]).call(mychart);
    mychart.zoomRect(true);
    webreduce.callbacks.resize_center = mychart.autofit;
    
    // set up plot control buttons and options:
    if (d3.select("#plot_controls").attr("plot_type") != "1d") {
      // then make the controls:
      var plot_controls = d3.select("#plot_controls")
      plot_controls.attr("plot_type", "1d")
      plot_controls.selectAll("select,input,button,label").remove();
      plot_controls.selectAll(".scale-select")
        .data(["xscale", "yscale"])
        .enter().append("label")
        .classed("scale-select", true)
        .text(function(d) {return d})
        .append("select")
          .attr("id", function(d) {return d})
          .attr("axis", function(d) {return d[0]})
          .on("change", function() {
            var axis = d3.select(this).attr("axis") + "transform",
                transform = this.value;
            webreduce.editor._active_plot[axis](transform);  
          })
          .selectAll("option").data(["linear", "log"])
            .enter().append("option")
            .attr("value", function(d) {return d})
            .text(function(d) {return d})
      
      plot_controls.selectAll(".show-boxes")
        .data(["errorbars", "points", "line"])
        .enter().append("label")
        .classed("show-boxes", true)
        .text(function(d) {return d})
        .append("input")
          .attr("id", function(d) {return "show_" + d})
          .attr("type", "checkbox")
          .attr("checked", "checked")
          .on("change", function() {
            var o = mychart.options();
            o[this.id] = this.checked;
            webreduce.editor._active_plot.options(o).update();
          });
          
      plot_controls
        .append("input")
          .attr("type", "button")
          .attr("id", "export_data")
          .attr("value", "export")
          .on("click", webreduce.editor.export_data)
      
      plot_controls
        .append("input")
          .attr("type", "button")
          .attr("id", "download_svg")
          .attr("value", "\u2B63 svg")
          .on("click", function() {
            var chart = webreduce.editor._active_plot;
            var svg = chart.export_svg();
            var serializer = new XMLSerializer();
            var output = serializer.serializeToString(svg);
            var filename = prompt("Save svg as:", "plot.svg");
            if (filename == null) {return} // cancelled
            webreduce.download(output, filename);
          });
    }
    
    return mychart
  }

  webreduce.editor.stash_data = function(suggested_name) {
    // embed the active template in a subroutine, exposing the
    // currently active output.  Store the structure in the 
    // browser.
    if (!window.localStorage) {alert("localStorage not supported in your browser"); return }
    
    var suggested_name = (suggested_name == null) ?  "processed" : suggested_name;
    var stashname = prompt("stash data as:", suggested_name);
    if (stashname == null) {return} // cancelled
    
    var existing_stashes = JSON.parse(localStorage['webreduce.editor.stashes'] || "{}");
    //var existing_stashnames = Object.keys(existing_stashes);
    
    if (existing_stashes.hasOwnProperty(stashname)) {
      var overwrite = confirm("stash named " + stashname + " already exists.  Overwrite?");
      if (!overwrite) {return}
    }
    
    var w = webreduce.editor,
      node = w._active_node,
      terminal = w._active_terminal,
      template = w._active_template;
    var template_copy = jQuery.extend(true, {}, template);
    var subroutine = {};
    subroutine.module = "user.stashed"
    subroutine.title = stashname;
    subroutine.module_def = {
      "template": template_copy,
      "inputs": [],
      "fields": [],
      "outputs": [{"source_module": node, "source_terminal": terminal, "terminal_id": "stashed"}],
      "action_id": "subroutine",
      "description": "previously processed data"
    }
    existing_stashes[stashname] = subroutine;
    localStorage['webreduce.editor.stashes'] = JSON.stringify(existing_stashes);
    webreduce.editor.load_stashes(existing_stashes);
  }
  
  webreduce.editor.load_stashes = function(stashes) {
    var existing_stashes = stashes || JSON.parse(localStorage['webreduce.editor.stashes'] || "{}");
    var stashnames = Object.keys(existing_stashes);
    d3.select("div#stashedlist").selectAll("ul").remove();
    var stashedlist = d3.select("div#stashedlist")
      .style("padding-left", "10px")
      .append("ul")
      .style("list-style", "none")
      .style("padding", "0px")
      
    var sn = stashedlist.selectAll("li").data(stashnames)
      .enter().append("li");
      
    sn.each(function() {
      var li = d3.select(this);
      li.append("input")
        .attr("type", "checkbox")
        .classed("compare", true)
      li.append("span")
        .text(function(d) {return d})
      li.append("span")
        .classed("stash-reload", true)
        .style("color", "blue")
        .text("reload")
        .on('click', function(d) {reload_stash(d)});
      li.append("span")
        .classed("stash-remove", true)
        .style("color", "red")
        .text("remove")
        .on('click', function(d) {remove_stash(d)});
      });
      
      stashedlist.selectAll("span.stash-remove, span.stash-reload")
        .style("text-decoration", "underline")
        .style("font-style", "italic")
        .style("cursor", "pointer")
        .style("padding-left", "10px")
        
      stashedlist.selectAll("input.compare")
        .on("change", function(d,i) {
          var checked = stashedlist.selectAll("input.compare:checked");
          var comparelist = [];
          checked.each(function(dd,ii) {comparelist.push(dd)});
          compare_stashed(comparelist);
        })
        
      
    //console.log(JSON.stringify(subroutine, null, 2));    
  }
  
  function remove_stash(stashname) {
    var existing_stashes = JSON.parse(localStorage['webreduce.editor.stashes'] || "{}");
    if (stashname in existing_stashes) {
      delete existing_stashes[stashname];
      localStorage['webreduce.editor.stashes'] = JSON.stringify(existing_stashes);
      webreduce.editor.load_stashes();
    }
  }
  
  function reload_stash(stashname) {
    var overwrite = confirm("discard active template to load stashed?");
    if (!overwrite) {return}
    var existing_stashes = JSON.parse(localStorage['webreduce.editor.stashes'] || "{}");
    if (stashname in existing_stashes) {
      var stashed = existing_stashes[stashname];
      var template = stashed.module_def.template;
      var node = stashed.module_def.outputs[0].source_module;
      var terminal = stashed.module_def.outputs[0].source_terminal;
      webreduce.editor.load_template(template, node, terminal);
    }
  }
  
  function compare_stashed(stashnames) {
    // stashnames is a list of stashed data ids
    // eventually send these as-is to server, but for now since the server
    // doesn't handle subroutines...
    d3.selectAll("g.module .selected").classed("selected", false);
    var existing_stashes = JSON.parse(localStorage['webreduce.editor.stashes'] || "{}");
    var stashnames = stashnames.filter(function(s) {return (s in existing_stashes)});
    var recalc_mtimes = $("#auto_reload_mtimes").prop("checked");
    var params_to_calc = stashnames.map(function(stashname) {
      var stashed = existing_stashes[stashname];
      return {
        template: stashed.module_def.template,
        config: {},
        node: stashed.module_def.outputs[0].source_module,
        terminal: stashed.module_def.outputs[0].source_terminal,
        return_type: "metadata"
      }
    });
    return webreduce.editor.calculate(params_to_calc, recalc_mtimes)
      .then(function(results) {
        if (results.length < 1) { return }
        var first = results[0];
        for (var i=1; i<results.length; i++) {
          if (results[i].datatype == first.datatype) {
            first.values = first.values.concat(results[i].values);
          }
        }
        webreduce.editor.show_plots(first);
      });
  }
  
  webreduce.editor.get_versioned_template = function(template) {
    var versioned = jQuery.extend(true, {}, template),
        editor = this,
        module_list = versioned.modules;
    module_list.forEach(function(m) {
      if (m.module && m.module in editor._module_defs) {
        m.version = editor._module_defs[m.module].version;
      }
    });
    return versioned
  }

  webreduce.editor.get_cached_timestamps = function() {
    var cache = this._cache;
    return this._cache.allDocs({"include_docs": true})
      .then(function(res) {
        return res.rows.map(function(r) {return [r.doc.created_at, r.doc._id]})
      })
  }

  function calculate_one(params, caching) {
    var r = new Promise(function(resolve, reject) {resolve()});
    var template = params.template,
        config = params.config || {},
        node = params.node,
        terminal = params.terminal,
        return_type = params.return_type || 'metadata';
        
    if (caching) {
      var versioned = webreduce.editor.get_versioned_template(template), 
          sig = Sha1.hash(JSON.stringify({
            method: "calculate",
            template: versioned,
            config: config,
            node: node,
            terminal: terminal,
            return_type: return_type }))
      r = r.then(function() { 
        return webreduce.editor._cache.get(sig).then(function(cached) {return cached.value})
        .catch(function(e) {
          return webreduce.server_api.calc_terminal(versioned, config, node, terminal, return_type)
            .then(function(result) {
              var doc = {
                _id: sig, 
                created_at: Date.now(),
                value: result 
              }
              webreduce.editor._cache.put(doc);
              return result
            })
            .catch(function(e) {
              console.log("error", e)
            })
        })
      })
    } else {
      r = r.then(function() { return webreduce.server_api.calc_terminal(template, config, node, terminal, return_type) })
    }
    return r
  }
  
  webreduce.editor.calculate = function(params, recalc_mtimes, noblock, result_callback) {
    //var recalc_mtimes = $("#auto_reload_mtimes").prop("checked");
    // call result_callback on each result individually (this function will return all results
    // if you want to act on the aggregate after)
    var caching = $("#cache_calculations").prop("checked");
    if (webreduce.editor._calc_status_message == null) {
      var status_message = $("<div />");
      status_message.append($("<h1 />", {text: "Processing..."}));
      status_message.append($("<progress />"));
      status_message.append($("<span />"));
      status_message.append($("<button />", {text: "cancel", class: "cancel"}));
      webreduce.editor._calc_status_message = status_message;
    }
    webreduce.editor._calculation_cancelled = false;
    var calc
    var status_message = webreduce.editor._calc_status_message;
    var r = new Promise(function(resolve, reject) {resolve()});
    var cancel_promise = new Promise(function(resolve, reject) { 
      status_message.find("button").on("click", function() {
        webreduce.editor._calculation_cancelled = true;
        resolve({"cancelled": true})
      });
    });
    if (!noblock) {
      r = r.then(function() { $.blockUI({message: status_message}) })
    }
    if (recalc_mtimes) {
      r = r.then(function() { return Promise.race([cancel_promise, webreduce.update_file_mtimes()])})
    }
    if (params instanceof Array) {
      var results = [],
          numcalcs = params.length;
      status_message.find("progress").attr("max", numcalcs.toFixed());
      params.forEach(function(p,i) {
        r = r.then(function() {
          if (webreduce.editor._calculation_cancelled) {
            return {"cancelled": true}
          }
          return Promise.race(
            [cancel_promise, calculate_one(p, caching).then(function(result) {
              if (result_callback) {result_callback(r, p, i);}
              status_message.find("span").text((i+1).toFixed() + " of " + numcalcs.toFixed());
              status_message.find("progress").val(i+1);
              results.push(result);
            })]
          )
        })
      });
      r = r.then(function() { return results })
    }
    else {
      r = r.then(function() {return Promise.race([cancel_promise, calculate_one(params, caching)])})
    }
    if (!noblock) {
      r = r.then(function(result) { $.unblockUI(); return result; })
       .catch(function(err) { $.unblockUI(); throw err });
    }
    return r;
  }
  
  webreduce.editor.export_data = function(suggested_name) {
    var suggested_name = (suggested_name == null) ?  "myfile.refl" : suggested_name;
    var filename = prompt("Export data as:", suggested_name);
    if (filename == null) {return} // cancelled
    var w = webreduce.editor,
      params = {
		template: w._active_template,
        config: {},
        node: w._active_node,
        terminal: w._active_terminal,
        return_type: "export"
      },
      recalc_mtimes = $("#auto_reload_mtimes").prop("checked");
    webreduce.editor.calculate(params, recalc_mtimes).then(function(result) {
      // add the template and target node, terminal to the header of the file:
      var header = {template_data: {template: params.template, node: params.node, terminal: params.terminal}};
      webreduce.download('# ' + JSON.stringify(header).slice(1,-1) + '\n' + result.values.join('\n\n'), filename);
    });       
  }
  
  webreduce.editor.accept_parameters = function(target, active_module) {
    target.selectAll("div.fields")
      .each(function(data) {
        if (!data.passthrough) {
          if (!active_module.config) {active_module.config = {}};
          active_module.config[data.id] = data.value;
        }
      });
  }
  
  webreduce.editor.make_fieldUI = {}; // generators for field datatypes
  
  webreduce.editor.make_fieldUI.fileinfo = function(field, active_template, datum, module_def, target, datasets_in) {
    // this will add the div only once, even if called twice.
    $("#navigation").unblock();
    target.selectAll("div#fileinfo").data([0])
      .enter()
        .append("div")
        .attr("id", "fileinfo")
    
    datum.value = datum.value || []; // insert empty list if value is null or missing
    var existing_count = datum.value.length;
    var radio = target.select("div#fileinfo").append("div")
      .classed("fields", true)
      .datum(datum)
    radio.append("input")
      .attr("id", field.id)
      .attr("type", "radio")
      .attr("name", "fileinfo");
    radio.append("label")
      .attr("for", field.id)
      .text(field.id + "(" + existing_count + ")");
    
    // jquery events handler for communications  
    $(radio.node()).on("fileinfo.update", function(ev, info) {
      if (radio.select("input").property("checked")) {
          radio.datum({id: field.id, value: info});
      } 
    });

    target.select("#fileinfo input").property("checked", true); // first one
    target.selectAll("div#fileinfo input")
      .on("click", null)
      .on("click", function() {
        $(".remote-filebrowser").trigger("fileinfo.update", d3.select(this).datum());
      });
    $("#fileinfo").buttonset();
    $(".remote-filebrowser").trigger("fileinfo.update", d3.select("div#fileinfo input").datum());
    // if there is data loaded, an output terminal is selected... and will be plotted instead
    if (datasets_in == null) { webreduce.handleChecked() };
    return radio    
  }
  
  webreduce.editor.make_fieldUI.index = function(field, active_template, datum_in, module_def, target, datasets_in) {
    if (target.select("div#indexlist").empty()) {
      target.append("div")
        .attr("id", "indexlist")
    }
    
    var datasets = datasets_in.values;
    // now have a list of datasets.
    var datum = jQuery.extend(true, {}, datum_in);
    datasets.forEach(function(d,i) {
      datum.value[i] = datum.value[i] || [];
    });
    
    function prettyJSON(d) {
      return "[\n  " + d.map(JSON.stringify).join(",\n  ") + "\n]"
    }
    
    var index_div = target.select("div#indexlist").append("div")
      .classed("fields", true)
      .datum(datum)
    var index_label = index_div.append("label")
      .text(field.id);
    var input = index_label.append("textarea")
      //.attr("type", "text")
      .attr("rows", datum.value.length + 2)
      .attr("field_id", field.id)
      .style("vertical-align", "middle")
      //.text(JSON.stringify(datum.value, null, 2))
      .text(prettyJSON(datum.value))
      .on("change", function(d) {
        //console.log("changing:", this, d);
        datum.value = JSON.parse(this.value);
        update_plot();
      });
      
    var drag_instance = webreduce.editor._active_plot.drag;
    var selector = new rectangleSelect(drag_instance);
    webreduce.editor._active_plot.interactors(selector);
    var select_active = true;
    
    var onselect = function(xmin, xmax, ymin, ymax) {
      d3.selectAll("#plotdiv svg g.series").each(function(d,i) {
        // i is index of dataset
        var series_select = d3.select(this);
        var index_list = datum.value[i];
        series_select.selectAll(".dot").each(function(dd, ii) {
          // ii is the index of the point in that dataset.
          var x = dd[0], 
              y = dd[1];
          if (x >= xmin && x <= xmax && y >= ymin && y <= ymax) {
            var dot = d3.select(this);
            dot.classed("masked", select_active);
            // manipulate data list directly:
            var index_index = index_list.indexOf(ii);
            if (index_index > -1 && !select_active) { 
              // then the index exists, but we're deselecting:
              index_list.splice(index_index, 1); 
            }
            else if (index_index < 0 && select_active) {
              // then the index doesn't exist and we're selecting
              index_list.push(ii); 
            }
          }
        });
        index_list.sort();
      });
      index_div.datum(datum);
      input.text(prettyJSON(datum.value));
    }
    
    selector.callbacks(onselect);
    
    var select_select = target.append("div")
      .style("background-color", "LightYellow")
      .classed("zoom-select-select", true)
      .append("form")
    
    select_select.append("span")
      .text("left-click mouse:")
      .append("br")
    
    select_select
      .append("label")
      .text("zoom")
      .append("input")
      .attr("name", "select_select")
      .attr("type", "radio")
      .attr("value", "zoom")
      .property("checked", true)
    
    select_select
      .append("label")
      .text("select")
      .append("input")
      .attr("name", "select_select")
      .attr("type", "radio")
      .attr("value", "select")
      
    select_select
      .append("label")
      .text("deselect")
      .append("input")
      .attr("name", "select_select")
      .attr("type", "radio")
      .attr("value", "deselect")

    var selectorchange = function(ev) {
      if (this.value == 'zoom') {
        webreduce.editor._active_plot.zoomRect(true);
        selector.selectRect(false);
      }
      else if (this.value == 'select') {
        select_active = true;
        webreduce.editor._active_plot.zoomRect(false);
        selector.selectRect(true);
      }
      else if (this.value == 'deselect') {
        select_active = false;
        webreduce.editor._active_plot.zoomRect(false);
        selector.selectRect(true);
      }
    }
    
    select_select.selectAll("input").on("change", selectorchange);
    selectorchange.call({value: "zoom"});
    
    //webreduce.editor.show_plots(datasets);
    
    function update_plot() {
      d3.selectAll("#plotdiv svg g.series").each(function(d,i) {
        // i is index of dataset
        var series_select = d3.select(this);
        var index_list = datum.value[i];
        series_select.selectAll("circle.dot")
          .filter(function(dd,ii) {return (index_list.indexOf(ii) > -1)})
          .classed("masked", true);
      })
    }
    
    update_plot();
    
    d3.selectAll("#plotdiv .dot").on("click", null); // clear previous handlers
    d3.selectAll("#plotdiv svg g.series").each(function(d,i) {
      // i is index of dataset
      var series_select = d3.select(this);
      series_select.selectAll(".dot").on("click", function(dd, ii) {
        // ii is the index of the point in that dataset.
        d3.event.stopPropagation();
        d3.event.preventDefault();
        var dot = d3.select(this);          
        // manipulate data list directly:
        var index_list = datum.value[i];
        var index_index = index_list.indexOf(ii);
        if (index_index > -1) { 
          index_list.splice(index_index, 1); 
          dot.classed("masked", false); 
        }
        else {
          index_list.push(ii); 
          dot.classed("masked", true);
        }
        index_list.sort();
        // else, pull masked dot list from class:
        // (this has the advantage of always being ordered inherently)
        /*
        dot.classed("masked", !dot.classed("masked")); // toggle selection
        datum.value[i] = [];
        series_select.selectAll(".dot").each(function(ddd, iii) {if (d3.select(this).classed("masked")) {datum.value[i].push(iii)}});
        */
        index_div.datum(datum);
        input.text(prettyJSON(datum.value));
      });
    });
    return input;
  }
  
  webreduce.editor.make_fieldUI.scale = function(field, active_template, datum, module_def, target, datasets_in) {
    target.selectAll("div#scalelist").data([0])
      .enter()
        .append("div")
        .attr("id", "scalelist")
    
    var datasets = datasets_in.values;
    original_datum = [];
    // now have a list of datasets.
    datum.value = datum.value.slice(0,datasets.length);
    datasets.forEach(function(d,i) {
      datum.value[i] = (datum.value[i] == null) ? 1 : datum.value[i];
      original_datum[i] = datum.value[i];
    });
    var scale_div = target.select("div#scalelist").append("div")
      .classed("fields", true)
      .datum(datum)
    var scale_label = scale_div.append("label")
      .text(field.id);
    var input = scale_label.append("textarea")
      //.attr("type", "text")
      .attr("rows", datum.value.length + 2)
      .attr("field_id", field.id)
      .style("vertical-align", "middle")
      .text(JSON.stringify(datum.value, null, 2))
      .on("change", function(d) { datum.value = JSON.parse(this.value) });
    
    unscaled_data = [];
    d3.selectAll("#plotdiv .dot").on("click", null); // clear previous handlers
    d3.selectAll("#plotdiv svg g.series").each(function(d,i) {
      // i is index of dataset
      // make a copy of the data:
      unscaled_data[i] = $.extend(true, [], d);
      var dragmove_point = function(dd,ii) {
        var chart = webreduce.editor._active_plot;
        var y = chart.y(),
            x = chart.x();
        var new_x = x.invert(d3.event.x),
          new_y = chart.y().invert(d3.event.y),
          old_point = unscaled_data[i][ii],
          old_x = old_point[0],
          old_y = old_point[1],
          new_scale = new_y / old_y;
        d.forEach(function(ddd, iii) {
          var old_point = unscaled_data[i][iii];
          ddd[1] = new_scale * old_point[1];
          if (ddd[2] && ddd[2].yupper != null) {
            ddd[2].yupper = new_scale * old_point[2].yupper;
          }
          if (ddd[2] && ddd[2].ylower != null) {
            ddd[2].ylower = new_scale * old_point[2].ylower;
          }
        })
        datum.value[i] = new_scale * original_datum[i];
        input.text(JSON.stringify(datum.value, null, 2));
        chart.update();
      }
      var drag_point = d3.behavior.drag()
        .on("drag", dragmove_point)
        .on("dragstart", function() { d3.event.sourceEvent.stopPropagation(); });
      var series_select = d3.select(this);
      series_select.selectAll(".dot")
        .attr("r", 5) // bigger for easier drag...
        .call(drag_point)
    });
    return input;
  }

  webreduce.editor.make_fieldUI.str = function(field, active_template, datum, module_def, target, datasets_in) {
    var input = target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("input")
          .attr("type", "text")
          .attr("field_id", field.id)
          .attr("value", datum.value)
          .on("change", function(d) { datum.value = this.value });
    return input;
  }
  
  webreduce.editor.make_fieldUI.opt = function(field, active_template, datum, module_def, target, datasets_in) {
    var input = target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("select")
          .attr("field_id", field.id)
          .attr("value", datum.value)
          .on("change", function(d) { datum.value = this.value })
    input
          .selectAll("option").data(field.typeattr.choices)
            .enter().append("option")
            .attr("value", function(d) {return d[1]})
            .property("selected", function(d) {return d[1] == datum.value})
            .text(function(d) {return d[0]})
    return input;
  }
  
  webreduce.editor.make_fieldUI.float = function(field, active_template, datum, module_def, target, datasets_in) {
    var input;
    if (field.multiple) { 
      //datum.value = [datum.value]; 
      input = target.append("div")
        .classed("fields", true)
        .datum(datum)
        .append("label")           
          .text(field.label)
          .append("input")
            .attr("type", "text")
            .attr("field_id", field.id)
            .attr("value", JSON.stringify(datum.value))
            .on("change", function(d) { datum.value = JSON.parse(this.value) });
    } else {
      input = target.append("div")
        .classed("fields", true)
        .datum(datum)
        .append("label")
          .text(field.label)
          .append("input")
            .attr("type", "number")
            .attr("field_id", field.id)
            .attr("value", datum.value)
            .on("change", function(d) { datum.value = parseFloat(this.value) });
    }
    return input;
  }

  webreduce.editor.make_fieldUI.float_expand = function(field, active_template, value, module_def, target, datasets_in) {
    var active_module = active_template.modules[module_index];
    var value = (active_module.config && field.id in active_module.config) ? active_module.config[field.id] : field.default;
    var datum = {id: field.id, value: value};
    if (field.multiple) { 
      //datum.value = [datum.value]; 
      target.append("div")
        .classed("fields", true)
        .datum(datum)
        .append("label")           
          .text(field.label)
          .append("input")
            .attr("type", "text")
            .attr("field_id", field.id)
            .attr("value", JSON.stringify(datum.value))
            .on("change", function(d) { datum.value = JSON.parse(this.value) });
    } else {
      target.append("div")
        .classed("fields", true)
        .datum(datum)
        .selectAll("label").data(d3.range(datasets_in.values.length))
          .enter().append("label")
          .text(field.label)
          .append("input")
            .attr("type", "number")
            .attr("value", function(d,i) {return (value instanceof Array)? value[i] : value})
            .on("change", function(d,i) { 
              if (!(datum.value instanceof Array)) {
                var new_value = d3.range(datasets_in.values.length).map(function() {return datum.value})
                datum.value = new_value;
              }
              datum.value[i] = parseFloat(this.value);
            });
    }
  }
  
  webreduce.editor.make_fieldUI.int = function(field, active_template, datum, module_def, target) {
    var input = target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("input")
          .attr("type", "number")
          .attr("field_id", field.id)
          .attr("value", datum.value)
          .on("change", function(d) { datum.value = parseInt(this.value) });
    return input;
  }
  
  webreduce.editor.make_fieldUI.bool = function(field, active_template, datum, module_def, target) {
    var input = target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("input")
          .attr("type", "checkbox")
          .attr("field_id", field.id)
          .property("checked", datum.value)
          .on("change", function(d) { datum.value = this.checked });
    return input;
  }
  
  webreduce.editor.fileinfo_update = function(fileinfo) {
    $(".remote_filebrowser").trigger("fileinfo.update", [fileinfo]);
  }

  webreduce.editor.load_instrument = function(instrument_id) {
    var editor = this;
    editor._instrument_id = instrument_id;
    return webreduce.server_api.get_instrument(instrument_id)
      .then(function(instrument_def) {
        editor._instrument_def = instrument_def;
        editor._module_defs = {};
        if ('modules' in instrument_def) {
          for (var i=0; i<instrument_def.modules.length; i++) {
            var m = instrument_def.modules[i];
            editor._module_defs[m.id] = m;
          }
        }
        // load into the editor instance
        editor._instance.module_defs(editor._module_defs);
        // pass it through:
        return instrument_def;
      })
  }
  
  webreduce.editor.switch_instrument = function(instrument_id) {
    return this.load_instrument(instrument_id)
      .then(function(instrument_def) { 
          var template_names = Object.keys(instrument_def.templates);
          $("#main_menu #predefined_templates ul").empty();
          template_names.forEach(function (t,i) {
            $("#main_menu #predefined_templates ul").append($("<li />", {text: t}));
            $("#main_menu").menu("refresh");
          })
          var default_template = template_names[0];
          if (localStorage) {
            var lookup_id = "webreduce.instruments." + instrument_id + ".last_used_template";
            var test_template_name = localStorage.getItem(lookup_id);
            if (test_template_name != null && test_template_name in instrument_def.templates) {
              default_template = test_template_name;
            }
          }
          current_instrument = instrument_id;
          var template_copy = jQuery.extend(true, {}, instrument_def.templates[default_template]);
          return webreduce.editor.load_template(template_copy);
        });
  }
  
  webreduce.editor.edit_template = function(template_def, instrument_id) {
    var template_def = template_def || this._active_template;
    var instrument_id = instrument_id || this._instrument_id;
    var post_load = function() {
      var te = webreduce.editor._active_template_editor;
      te.load_instrument(instrument_id)
          .then(function(){
            te.e.import(template_def);
          })
      d3.select(te.document.getElementById("apply_changes")).on('click', function() {
        webreduce.editor.load_template(te.e.export());
      });
    }
    if (this._active_template_editor == null || this._active_template_editor.closed) {
      var te = window.open("template_editor_live.html", "template_editor", "width=960,height=480");
      this._active_template_editor = te;
      te.addEventListener('editor_ready', post_load, false);
    }
  }
  
  webreduce.editor.load_template = function(template_def, selected_module, selected_terminal) {
    this._active_template = template_def;
    var template_sourcepaths = webreduce.getAllTemplateSourcePaths(template_def),
        browser_sourcepaths = webreduce.getAllBrowserSourcePaths();
    for (var source in template_sourcepaths) {
      var paths = template_sourcepaths[source];
      for (var path in paths) {
        if (browser_sourcepaths.findIndex(function(sp) {return sp.source == source && sp.path == path}) < 0) {
          webreduce.addDataSource("navigation", source, path.split("/"));
        }
      }
    }
    var target = d3.select("#" + this._target_id);
    this._instance.import(template_def);

    target.selectAll(".module").classed("draggable wireable", false);
    target.selectAll("g.module").on("click", webreduce.editor.handle_module_clicked);
    //target.selectAll("g.module").on("contextmenu", webreduce.editor.handle_module_contextmenu);
    
    autoselected = template_def.modules.findIndex(function(m) {
      var has_fileinfo = webreduce.editor._module_defs[m.module].fields
        .findIndex(function(f) {return f.datatype == 'fileinfo'}) > -1
      return has_fileinfo;
    });
    
    if (selected_module != null) {
      autoselected = selected_module;
    }
    
    if (autoselected > -1) {
      var toselect = target.selectAll('.module')
        .filter(function(d,i) { return i == autoselected })
      // choose the module directly by default
      var toselect_target = toselect.select(".title").node();
      // but if a terminal is specified, use that as target instead.
      if (selected_terminal != null) {
        var term = toselect.select('rect.terminal[terminal_id="'+selected_terminal+'"]').node();
        if (term != null) {toselect_target = term} // override the selection with terminal
      }
      webreduce.editor.handle_module_clicked.call(toselect.node(), toselect.datum(), autoselected, toselect_target); 
    }
    
  }
  
  
})();
