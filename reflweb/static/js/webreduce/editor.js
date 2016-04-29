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

  webreduce.editor.create_instance = function(target_id) {
    // create an instance of the dataflow editor in
    // the html element referenced by target_id
    this._instance = new dataflow.editor();
    this._target_id = target_id;
    this._instance.data([{modules:[],wires: []}]);
    var target = d3.select("#" + target_id);
    target.call(this._instance);
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
    var data_to_show;
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
    
    var buttons_div = config_target.append("div")
      .classed("control-buttons", true)
      .style("position", "absolute")
      .style("bottom", "10px")
    buttons_div.append("button")
      .text("accept")
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
      .on("click", function() {
        console.log(config_target, active_module);
        if (active_module.config) { delete active_module.config }
        webreduce.editor.handle_module_clicked.call(elem,d,i,clicked_elem);
      })
      
    $(buttons_div).buttonset();
    
    var data_show_promise = (data_to_show == undefined) ? new Promise(function(r,j) {r(null)}) : 
      webreduce.server_api.calc_terminal(active_template, {}, i, data_to_show, "metadata");
    
    data_show_promise.then(function(datasets_in) {
      webreduce.editor.show_plots(datasets_in);
      fields.forEach(function(field) {
        if (webreduce.editor.make_fieldUI[field.datatype]) {
          webreduce.editor.make_fieldUI[field.datatype](field, active_template, i, module_def, config_target, datasets_in);
        }
      });
      return datasets_in;
    })
    .then(function() {
      
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
        .append("div")
        .classed("paramsDisplay", true)
        .text(function(d) {return JSON.stringify(d)})
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
    options.xtransform = $("#xscale").val();
    options.ytransform = $("#yscale").val();
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
    }
    
    return mychart
  }

  webreduce.editor.export_data = function() {
    var filename = prompt("Export data as:", "myfile.refl");
    if (filename == null) {return} // cancelled
    var w = webreduce.editor,
      node = w._active_node,
      terminal = w._active_terminal,
      template = w._active_template;
    webreduce.server_api.calc_terminal(template, {}, node, terminal, 'export').then(function(result) {
      // add the template and target node, terminal to the header of the file:
      var header = {template: template, node: node, terminal: terminal};
      webreduce.download('#' + JSON.stringify(header) + '\n' + result.values.join('\n\n'), filename);
    });       
  }
  
  webreduce.editor.accept_parameters = function(target, active_module) {
    target.selectAll("div.fields")
      .each(function(data) {
        if (!active_module.config) {active_module.config = {}};
          active_module.config[data.id] = data.value;
      });
  }
  
  webreduce.editor.make_fieldUI = {}; // generators for field datatypes
  
  webreduce.editor.make_fieldUI.fileinfo = function(field, active_template, module_index, module_def, target, datasets_in) {
    // this will add the div only once, even if called twice.
    $("#navigation").unblock();
    target.selectAll("div#fileinfo").data([0])
      .enter()
        .append("div")
        .attr("id", "fileinfo")
    
    var active_module = active_template.modules[module_index];
    var datum = {"id": field.id, value: []},
        existing_count = 0;
    if (active_module.config && active_module.config[field.id] ) {
      existing_count = active_module.config[field.id].length;
      datum.value = active_module.config[field.id];
    }
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
  }
  
  webreduce.editor.make_fieldUI.index = function(field, active_template, module_index, module_def, target, datasets_in) {
    target.selectAll("div#indexlist").data([0])
      .enter()
        .append("div")
        .attr("id", "indexlist")
    
    var active_module = active_template.modules[module_index];

    var datum = {"id": field.id, value: []};
    if (active_module.config && active_module.config[field.id] ) {
      datum.value = active_module.config[field.id];
    }
    var index_div = target.select("div#indexlist").append("div")
      .classed("fields", true)
      .datum(datum)
    var index_label = index_div.append("label")
      .text(field.id);
    var display = index_label.append("div")
      .classed("value-display", true)
    display.text(JSON.stringify(datum.value));
    
    var datasets = datasets_in.values;
    // now have a list of datasets.
    datasets.forEach(function(d,i) {
      datum.value[i] = datum.value[i] || [];
    });
    //webreduce.editor.show_plots(datasets);
    datum.value.forEach(function(index_list, i) {
      var series_select = d3.select(d3.selectAll("#plotdiv svg g.series")[0][i]);
      index_list.forEach(function(index, ii) {
        series_select.select(".dot:nth-of-type(" + (index+1).toFixed() + ")").classed("masked", true);
      });
    });
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
        display.text(JSON.stringify(datum.value));
      });
    });
  }
  
  webreduce.editor.make_fieldUI.str = function(field, active_template, module_index, module_def, target) {
    var active_module = active_template.modules[module_index];
    var value = (active_module.config && field.id in active_module.config) ? active_module.config[field.id] : field.default;
    var datum = {"id": field.id, "value": value};
    target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("input")
          .attr("type", "text")
          .attr("field_id", field.id)
          .attr("value", value)
          .on("change", function(d) { datum.value = this.value });
  }
  
  webreduce.editor.make_fieldUI.opt = function(field, active_template, module_index, module_def, target) {
    var active_module = active_template.modules[module_index];
    var value = (active_module.config && field.id in active_module.config) ? active_module.config[field.id] : field.default;
    var datum = {"id": field.id, "value": value};
    target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("select")
          .attr("field_id", field.id)
          .attr("value", value)
          .on("change", function(d) { datum.value = this.value })
          .selectAll("option").data(field.typeattr.choices)
            .enter().append("option")
            .attr("value", function(d) {return d[1]})
            .property("selected", function(d) {return d[1] == value})
            .text(function(d) {return d[0]});
  }
  
  webreduce.editor.make_fieldUI.float = function(field, active_template, module_index, module_def, target, datasets_in) {
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
        .append("label")
          .text(field.label)
          .append("input")
            .attr("type", "number")
            .attr("field_id", field.id)
            .attr("value", value)
            .on("change", function(d) { datum.value = parseFloat(this.value) });
    }
  }

  webreduce.editor.make_fieldUI.float_expand = function(field, active_template, module_index, module_def, target, datasets_in) {
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
  
  webreduce.editor.make_fieldUI.int = function(field, active_template, module_index, module_def, target) {
    var active_module = active_template.modules[module_index];
    var value = (active_module.config && field.id in active_module.config) ? active_module.config[field.id] : field.default;
    var datum = {"id": field.id, "value": value};
    target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("input")
          .attr("type", "number")
          .attr("field_id", field.id)
          .attr("value", value)
          .on("change", function(d) { datum.value = parseInt(this.value) });
  }
  
  webreduce.editor.make_fieldUI.bool = function(field, active_template, module_index, module_def, target) {
    var active_module = active_template.modules[module_index];
    var value = (active_module.config && field.id in active_module.config) ? active_module.config[field.id] : field.default;   
    var datum = {"id": field.id, "value": value};
    target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("input")
          .attr("type", "checkbox")
          .attr("field_id", field.id)
          .property("checked", value)
          .on("change", function(d) { datum.value = this.checked });
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
    this.load_instrument(instrument_id)
      .then(function(instrument_def) { 
          var template_names = Object.keys(instrument_def.templates);
          $("#main_menu #predefined_templates ul").empty();
          template_names.forEach(function (t,i) {
            $("#main_menu #predefined_templates ul").append($("<li />", {text: t}));
            $("#main_menu").menu("refresh");
          })
          var default_template = template_names[0];
          current_instrument = instrument_id;
          webreduce.editor.load_template(instrument_def.templates[default_template]); 
        });
  }
  
  webreduce.editor.load_template = function(template_def) {
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
    
    var autoselected = template_def.modules.findIndex(function(m) {
      var has_fileinfo = webreduce.editor._module_defs[m.module].fields
        .findIndex(function(f) {return f.datatype == 'fileinfo'}) > -1
      return has_fileinfo;
    });
    
    if (autoselected > -1) {
      var toselect = target.select('.module[index="' + String(autoselected) + '"]');
      var toselect_title = toselect.select(".title").node();
      toselect.each(function(d,i) { webreduce.editor.handle_module_clicked.call(this, d, i, toselect_title)});
    }
  }
  
  
})();
