// require(d3.js, webreduce.server_api, dataflow)
// require(d3, dataflow)
export var editor = {};

import { app, download } from './main.js';
import {server_api} from './server_api/api_msgpack.js';
import {dependencies} from './deps.js';
//import {Sha1} from './sha1.es.js';
import {instruments} from './instruments/index.js';
// now a global...
import {zip} from './libraries.js';
import {d3} from './libraries.js';
import {extend, heatChart, heatChartMultiMasked, xyChart, dataflowEditor, colormap_names, get_colormap} from './libraries.js';
import {PouchDB} from './libraries.js';
import {sha1} from './libraries.js';
import {template_editor_url} from './libraries.js';
import {filebrowser} from './filebrowser.js';
import {make_fieldUI} from './fieldUI.js';
import { plotter  } from './plot.js';

editor.instruments = instruments;

editor.dispatch = d3.dispatch("accept", "field_update");

editor.guid = function() {
  var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random()*16|0,v=c=='x'?r:r&0x3|0x8;
    return v.toString(16);});
  return uuid;
}

class inMemoryCache {
  constructor() {
    this.storage = new Map();
    this.adapter = 'memory';
  }
  destroy() {
    this.storage = null;
  }
  async get(key) {
    let storage = this.storage;
    return new Promise(function(resolve, reject) {
      if (storage.has(key)) {
        resolve(storage.get(key));
      }
      else {
        reject("key not found: " + String(key));
      }
    });
  }
  put(key, value) {
    return this.storage.set(key, value);
  }
};

editor.make_cache = function() {
  try {
    this._cache = new PouchDB("calculations", {size: 100});
  } catch (e) {
    if (e.name === "SecurityError") {
      var warning = "Could not store website data - falling back to in-memory storage (may cause memory issues.)";
      warning += "Please adjust your privacy level to allow website data storage (unblock cookies?) and reload page.";
      alert(warning);
      this._cache = new inMemoryCache();
    } else {
      throw e;
    }
  }
}
editor.make_cache();

editor.clear_cache = function() {
  app.blockUI("clearing cache...", 1000);
  this._cache.destroy().then(function () {
    // cache destroyed, now create a new one
    editor.make_cache();
    app.unblockUI(1000);
  }).catch(function (err) {
    // error occurred
    app.unblockUI(1000);
    alert(err + "could not destroy cache");
  });
}

editor.create_instance = function(target_id) {
  // create an instance of the dataflow editor in
  // the html element referenced by target_id
  this._instance = new dataflowEditor(null, d3);
  this._target_id = target_id;
  //this._instance.data([{modules:[],wires: []}]);
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
  // add decoration filters and patterns for highlighting filled paths
  var defs = this._instance.svg().append("defs");
  var glow_filter = defs.append("filter")
    .attr("id", "glow")
    .attr("filterUnits", "objectBoundingBox")
    .attr("x", "-50%")
    .attr("y", "-50%")
    .attr("width", "200%")
    .attr("height", "200%")
  
  glow_filter.append("feOffset")
      .attr("result", "offOut")
      .attr("in", "SourceGraphic")
      .attr("dx", 0)
      .attr("dy", 0)
      
  glow_filter.append("feColorMatrix")
      .attr("in", "offOut")
      .attr("result", "matrixOut")
      .attr("type", "matrix")
      .attr("values", "0 0 0 0 0 \
                        1 1 1 1 0 \
                        0 0 0 0 0 \
                        0 0 0 1 0")
                        
  glow_filter.append("feGaussianBlur")
      .attr("in", "matrixOut")
      .attr("result", "blurOut")
      .attr("stdDeviation", 10);

  glow_filter.append("feBlend")
      .attr("in", "SourceGraphic")
      .attr("in2", "blurOut")
      .attr("mode", "normal")

  // on wires with data in them:
  // svg.selectAll("path.wire.filled").style("stroke-dasharray", null).style("stroke", "green");
  // svg.selectAll("path.wire.empty").style("stroke-dasharray", "2,2").style("stroke", "red");

  var output_pattern = defs.append("pattern")
    .attr("id", "output_hatch")
    .attr("patternUnits", "userSpaceOnUse")
    .attr("width", 10)
    .attr("height", 10)
    .append("path")
      .attr("d", "M-1,1 l2,-2 M0,10 l10,-10 M9,11 l2,-2")
      .style("stroke", "#88FFFF")
      .style("stroke-opacity", 1)
      .style("stroke-width", 3)
      
  var input_pattern = defs.append("pattern")
    .attr("id", "input_hatch")
    .attr("patternUnits", "userSpaceOnUse")
    .attr("width", 10)
    .attr("height", 10)
    .style("fill-opacity", 1)
    .append("path")
      .attr("d", "M-1,1 l2,-2 M0,10 l10,-10 M9,11 l2,-2")
      .style("stroke", "#88FF88")
      .style("stroke-opacity", 1)
      .style("stroke-width", 3)
}

function module_clicked_multiple() {
  var editor_select = d3.select("#" + editor._target_id);
  var active_template = editor._active_template;
  app.layout.collapse(2);
  var config_target = d3.select(".ui-layout-east");
  config_target.selectAll("div").remove();
  var to_compare = [];
  editor_select.selectAll("g.module").each(function(dd, ii) {
    d3.select(this).selectAll("g.selected rect.terminal").each(function(ddd,iii) {
      var tid = d3.select(this).attr("terminal_id");
      to_compare.push({"node": ii, "terminal": tid})
    });
  });
  compare_in_template(to_compare, active_template);
}

function module_clicked_single() {
  var active_template = editor._active_template;
  var editor_select = d3.select("#" + editor._target_id);
  var selected_terminal = editor_select.select("g.module g.selected rect.terminal");
  let data_to_show = (selected_terminal.empty()) ? null : selected_terminal.attr("terminal_id");
  editor._active_terminal = data_to_show;
  let i = editor._active_node;
  let active_module = active_template.modules[i];
  let module_def = editor._module_defs[active_module.module];
  let fields = module_def.fields || [];
  var add_interactors = (data_to_show == (module_def.inputs[0] || {}).id);

  // TODO: fix for split layout
  // webreduce.layout.open("east");
  var config_target = d3.select(".ui-layout-east");
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
    .text( $("#auto_accept_changes").prop("checked") ? "replot": "accept")
    .classed("accept config", true)
    .on("click", function() {
      editor.accept_parameters(config_target, active_module);
      if (selected_terminal.empty()) {
        // then it's a loader that's clicked, with no output selected;
        let first_output = module_def.outputs[0].id;
        let selected_title = editor_select.select("g.module g.title.selected");
        let module_elem = d3.select(selected_title.node().parentNode);
        module_elem.selectAll("g.terminals").classed('selected', function(d) { return d.id == first_output });
      }
      else if (!(selected_terminal.classed("output"))) {
        // find the first output and select that one...
        let first_output = module_def.outputs[0].id;
        let module_elem = d3.select(selected_terminal.node().parentNode.parentNode);
        module_elem.selectAll("g.terminals").classed('selected', function(d) { return d.id == first_output });
      }
      module_clicked_single();
    })
  buttons_div.append("button")
    .text("clear")
    .classed("clear config", true)
    .on("click", function() {
      //console.log('clear: ', config_target, JSON.stringify(active_module, null, 2));
      if (active_module.config) { delete active_module.config }
      module_clicked_single();
    })
    
  //$(buttons_div.node()).buttonset();
  
  var terminals_to_calculate = module_def.inputs.map(function(inp) {return inp.id});
  var fields_in = {};
  if (data_to_show != null && terminals_to_calculate.indexOf(data_to_show) < 0) {
    terminals_to_calculate.push(data_to_show);
  }
  var recalc_mtimes = $("#auto_reload_mtimes").prop("checked"),
      params_to_calc = terminals_to_calculate.map(function(terminal_id) {
        return {template: active_template, config: {}, node: i, terminal: terminal_id, return_type: "plottable"}
      })
  editor.calculate(params_to_calc, recalc_mtimes)
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
      .map(function(d) {return im[d.id]});
    field_inputs.forEach(function(d) {
      d.values.forEach(function(v) {
        extend(true, fields_in, v.params);
      });
    });
    editor.show_plots([datasets_in]);
    fields.forEach(function(field) {
      if (make_fieldUI[field.datatype]) {
        var value;
        var passthrough = false;
        var field_copy =  extend(true, {}, field);
        var default_value = field_copy.default;
        if (field.id in fields_in) {
          //value = fields_in[field.id];
          default_value = fields_in[field.id];
          passthrough = true;
        }
        if (active_module.config && field.id in active_module.config) {
          value = active_module.config[field.id];
        }
        
        var datum = {"id": field.id, "value": value, "default_value": default_value, "passthrough": passthrough};
        var fieldUImaker = make_fieldUI[field.datatype];
        var context = {
          field: field,
          active_template: active_template,
          datum: datum,
          module_def: module_def,
          target: config_target,
          datasets_in: datasets_in,
          active_module: active_module,
          add_interactors: add_interactors,
        }
        var fieldUI = fieldUImaker.call(context);
        var auto_accept = function() {
          //console.log(this, d3.select(this).datum(), 'changing!');
          if ($("#auto_accept_changes").prop("checked")) {
            editor.accept_parameters(config_target, active_module);
          }
        }
        //if (passthrough) {fieldUI.property("disabled", true)};
        fieldUI
          .on("input.auto_accept", auto_accept)
          .on("change.auto_accept", auto_accept)
        // add tooltip with description of parameter
        d3.select(fieldUI.node().parentNode).attr("title", field.description);
          
      }
    });
  });
}

editor.get_full = function() {
  console.log(this._active_node, this._active_template, this._active_terminal);
  let params_to_calc = {
    template: this._active_template,
    config: {},
    node: this._active_node,
    terminal: this._active_terminal,
    return_type: "full"
  }
  this.calculate(params_to_calc, true).then(function(result) {
    console.log(result);
  })
}

function module_clicked() {
  var editor_select = d3.select("#" + editor._target_id);
  if (editor_select.selectAll("g.module g.selected rect.terminal").size() > 1) {
    module_clicked_multiple();
  }
  else {
    module_clicked_single();
  }
}
editor.module_clicked = module_clicked;
editor.handle_module_clicked = function(d,i,current_group,clicked_elem) {
  // d module data, i is module index, elem is registered to catch event
  //
  // Flow: 
  //  - if the module title is clicked, show configuration and 
  //    data from the first input terminal.
  //  - if input terminal is clicked, show that data and configuration
  //  - if output terminal is clicked, show that data and configuration
  
  var editor_select = d3.select("#" + editor._target_id);
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
    editor_select.selectAll("g.module, g.module g.title").classed("selected", false);
    module_clicked_multiple();   
  }

  else {
    editor_select.selectAll(".module .selected").classed("selected", false);
    d3.select(clicked_elem.parentNode).classed("selected", true);
    
    var active_template = editor._active_template;
    var active_module = active_template.modules[i];
    var module_def = editor._module_defs[active_module.module];
    var fields = module_def.fields || [];
    if (fields.filter(function(d) {return d.datatype == 'fileinfo'}).length == 0) {
        var nav = $("#datasources");
        nav.find("div.block-overlay").show();
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
    
    
    editor._active_node = i;
    editor._active_terminal = data_to_show;

    module_clicked();
    
  }
}

function compare_in_template(to_compare, template) {
  var template = template || editor._active_template,
      recalc_mtimes = $("#auto_reload_mtimes").prop("checked");
      params_to_calc = to_compare.map(function(a) {
        return {template: template, config: {}, node: a.node, terminal: a.terminal, return_type: "plottable"}
      });
  return editor.calculate(params_to_calc, recalc_mtimes)
    .then(function(results) {
      editor.show_plots(results);
    });
}

editor.show_plots = function(results) {
  var new_plotdata;
  if (results.length == 0 || results[0] == null || results[0].values.length == 0) { 
    new_plotdata = null; 
  }
  else { 
    new_plotdata = {values: [], type: null, xcol: null, ycol: null}
    new_plotdata.type = results[0].values[0].type;
    results.forEach(function(r) {
      var values = r.values || [];
      values.forEach(function(v) {
        if (new_plotdata.type == null && v.type) {
          new_plotdata.type = v.type;
        }
        new_plotdata.values.push(v);
      });
    });
  }

    var active_plot;
    //d3.select("#plot_title").text("");
    // d3.select("#plotdiv").on("mouseover.setRawHandler", function() {
    //   d3.select("body").on("keydown.triggerRawDump", function() {
    //     if (d3.event.key.toLowerCase() == "r") {
    //       console.log(results);
    //     }
    //   })
    // });
    if (new_plotdata == null) {
      plotter.instance.setPlotData({type: 'null'});
      // active_plot = null;
      // d3.select("#plotdiv").selectAll("svg, div").remove();
      // d3.select("#plotdiv").classed("plot", false);
      // d3.select("#plotdiv").append("div")
      //   //.style("position", "absolute")
      //   .style("top", "0px")
      //   .style("text-align", "center")
      //   .append("h1").html("&#8709;")
    }
    else if (new_plotdata.type == '1d') {
      active_plot = this.show_plots_1d(new_plotdata);
    }
    else if (new_plotdata.type == 'nd') {
      plotter.instance.setPlotData(new_plotdata);
      //active_plot = this.show_plots_nd(new_plotdata);
    }
    else if (new_plotdata.type == '2d') {
      active_plot = this.show_plots_2d(new_plotdata);
    }
    else if (new_plotdata.type == '2d_multi') {
      active_plot = this.show_plots_2d_multi(new_plotdata);
    }
    else if (new_plotdata.type == 'params') {
      active_plot = this.show_plots_params(new_plotdata);
    }
    else if (new_plotdata.type == 'metadata') {
      active_plot = this.show_plots_metadata(new_plotdata);
    }
    this._active_plot = active_plot;
    return active_plot;
  }
  
  editor.show_plots_params = function(data) {
    var params = data.values.map(function(v) { return v.params });
    d3.selectAll("#plotdiv").selectAll("svg, div").remove();
    d3.select("#plotdiv").classed("plot", false);
    d3.select("#plotdiv").append("div")
      .classed("params_controls", true)
      .selectAll(".parambuttons").data(["open all", "close all"])
      .enter()
        .append("button")
        .attr("action", function(d) {return d.replace(" ", "_")})
        .text(function(d) { return d })
        .on("click", function(d) {
          let action = this.getAttribute("action");
          $("div.paramsDisplay").each(function() {
            $(this).jstree(action);
          });
        })
    let param_divs = d3.select("#plotdiv")
      .selectAll(".paramsDisplay")
      .data(params).enter()
        .append("div")
        .style("overflow", "auto")
        .classed("paramsDisplay", true)

    param_divs.each(function(d, i) {
      let tree = JSON_to_tree('#', d);
      tree.state = {opened: true};
      tree.text = String(i);
      $(this).jstree({
        "core": {"data": tree}
      });
    })
    return data
  }

  function JSON_to_tree(name, value) {
    console.log(name, value)
    let label = `<label>${name}</label>:`;
    if (value == null) {
      return {
        li_attr: {class: "json_null json_item"},
        icon: false,
        text: label + `<span>null</span>`
      }
    }
    else if (Array.isArray(value)) {
      let return_obj = {
        li_attr: {class: "json_array json_item"},
        icon:false
      }
      if (value.length > 0) {
        return_obj.text = label + `Array(${value.length})`;
        return_obj.children = value.map(function(v, n) { return JSON_to_tree(n, v) });
      }
      else {
        return_obj.text = label + " []";
      }
      return return_obj;
    }
    else if (value instanceof Object) {
      let entries = Object.entries(value);
      let return_obj = {
        li_attr: {class: "json_object json_item"},
        icon: false
      }
      if (entries.length > 0) {
        return_obj.text = label;
        return_obj.children = entries.map(function(nv) { return JSON_to_tree(nv[0], nv[1])});
      }
      else {
        return_obj.text = label + " {}";
      }
      return return_obj;
    }
    else if (typeof(value) == "number") {
      return {
        li_attr: {class: "json_number json_item"},
        icon: false,
        text: label + `<span>${value}</span>`
      }
    }
    else if (typeof(value) == "string") {
      return {
        li_attr: {class: "json_string json_item"},
        icon: false,
        text: label + `<span>${value}</span>`
      }
    }
  }

  editor.show_plots_metadata = function(data) {
    var metadata = data.values.map(function(v) { return v.values });
    var m0 = metadata[0] || {};
    var colset = new Set(Object.keys(m0));
    for (var nm of metadata.slice(1)) {
      for (var c of colset) {
        if (!(c in nm)) {
          colset.delete(c);
        }
      }
    }
    var cols = Array.from(colset);
    d3.selectAll("#plotdiv").selectAll("svg, div").remove();
    d3.select("#plotdiv").classed("plot", false);
    let metadata_table = d3.select("#plotdiv").append("div").append("table").classed("metadata", true)
    metadata_table
      .append("thead").append("tr")
      .selectAll(".colHeader")
      .data(cols).enter()
        .append("th")
        .classed("colHeader", true)
        .text(function(d) { return String(d) })
    
    metadata_table
      .append("tbody")
      .selectAll(".metadata-row")
      .data(metadata).enter()
        .append("tr")
        .classed("metadata-row", true)
        .on("click", function() {
          metadata_table.selectAll(".metadata-row")
            .classed("active", false);
          d3.select(this).classed("active", true);
        })
        .each(function(d) { 
          let row = d3.select(this);
          cols.forEach(function(c) {
            row.append("td").append("pre")
              //.attr("contenteditable", true)
              //.on("input", function(dd, ii) { 
              //  let new_text = this.innerText;
              //  let old_text = String(d[c]);
              //  let dirty = (old_text != new_text);
              //  d3.select(this.parentNode).classed("dirty", dirty);
              //})
              .text(String(d[c]));
          })
        });
    
    return metadata_table
  }

editor.show_plots_2d = function(plotdata) {
  var aspect_ratio = null,
      values = plotdata.values,
      mychart = editor._active_plot;
      
  // set up plot control buttons and options:
  if (d3.select("#plot_controls").attr("plot_type") != "2d") {
    // then make the controls:
    var plot_controls = d3.select("#plot_controls")
    plot_controls.attr("plot_type", "2d")
    plot_controls.selectAll("select,input,button,label").remove();
    var plot_select = plot_controls.selectAll(".plot-select")
      .data([0])
      .enter().append("label")
      .classed("plot-select", true)
      .text("dataset")
    plot_select
      .append("input")
        .attr("type", "number")
        .attr("min", "0")
        .style("width", "4em")
        .attr("value", 0)
        
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
          editor._active_plot[axis](transform);  
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
          editor._active_plot[this.id](this.checked);
        });
  
    plot_controls
      .append("input")
        .attr("type", "button")
        .attr("id", "export_data")
        .attr("value", "export")
        .on("click", editor.export_data)
      
    var colormap_select = plot_controls
      .append("label")
        .text("colormap")
      .append("select")
      .attr("id", "colormap_select")
      .on("change", function() {
        var new_colormap = get_colormap(this.value, d3);
        editor._active_plot.colormap(new_colormap).redrawImage();
        editor._active_plot.colorbar.update();
      })
    colormap_select
      .selectAll("option").data(colormap_names)
        .enter().append("option")
        .attr("value", function(d) {return d})
        .property("selected", function(d) {return d == 'jet'})
        .text(function(d) {return d})
  }
  
  if (!(mychart && mychart.type && mychart.type == "heatmap_2d")) {
    d3.selectAll("#plotdiv").selectAll("svg, div").remove();
    mychart = new heatChart({margin: {left: 100}}, d3);
    d3.selectAll("#plotdiv").data(values[0].z).call(mychart);
    app.callbacks.resize_center = function() {mychart.autofit()};
  }
      
  var update_plotselect = function() {
    //d3.select(this).datum(parseInt(this.value));
    //console.log(d3.select(this), d3.select(this).datum(), this.value);
    var plotnum = (this && this.value != null) ? parseInt(this.value) : 0,
        data = values[plotnum];
    var title = data.title || "";
    d3.select("#plot_title").text(title);
    data.ztransform = $("#zscale").val();
    if ((((data.options || {}).fixedAspect || {}).fixAspect || null) == true) {
      aspect_ratio = ((data.options || {}).fixedAspect || {}).aspectRatio || null;
    }
    
    //mychart = new heatChart();
    mychart
      //.ztransform($("#zscale").val())
      //.colormap(cm.get_colormap(current_instr == "NGBSANS" ? "spectral" : "jet"))
      .autoscale(true)
      .aspect_ratio(aspect_ratio)
      .dims(data.dims)
      .xlabel(data.xlabel)
      .ylabel(data.ylabel);
    //d3.selectAll("#plotdiv").selectAll("svg, div").remove();
    //d3.selectAll("#plotdiv").data(data.z).call(mychart);
    var new_colormap = get_colormap($("select#colormap_select").val(), d3);
    mychart.colormap(new_colormap);
    mychart.source_data(data.z[0]);
    mychart.zoomScroll(true);
    mychart.ztransform($("#zscale").val())
    
  }
  
  d3.select("#plot_controls .plot-select input")
    .attr("max", values.length-1)
    .on("change", update_plotselect)
    .on("click", update_plotselect)
    .on("input", update_plotselect)
  
  update_plotselect.call(null);
  mychart.interactors(null);
  mychart.autofit();
  return mychart
}

editor.show_plots_2d_multi = function(plotdata) {
  var aspect_ratio = null,
      values = plotdata.values,
      mychart = editor._active_plot;
  let options = {margin: {left: 100}};
  // set up plot control buttons and options:
  if (d3.select("#plot_controls").attr("plot_type") != "2d_multi") {
    // then make the controls:
    var plot_controls = d3.select("#plot_controls")
    plot_controls.attr("plot_type", "2d_multi")
    plot_controls.selectAll("select,input,button,label").remove();
    var plot_select = plot_controls.selectAll(".plot-select")
      .data([0])
      .enter().append("label")
      .classed("plot-select", true)
      .text("dataset")
    plot_select
      .append("input")
        .attr("type", "number")
        .attr("min", "0")
        .style("width", "4em")
        .attr("value", 0)
        
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
          editor._active_plot[axis](transform);  
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
          editor._active_plot[this.id](this.checked);
        });
    
    plot_controls
      .append("input")
        .attr("type", "button")
        .attr("id", "export_data")
        .attr("value", "export")
        .on("click", editor.export_data)
        
    var colormap_select = plot_controls
      .append("label")
        .text("colormap")
      .append("select")
      .attr("id", "colormap_select")
      .on("change", function() {
        var new_colormap = get_colormap(this.value, d3);
        editor._active_plot.colormap(new_colormap).redrawImage();
        editor._active_plot.colorbar.update();
      })
    colormap_select
      .selectAll("option").data(colormap_names)
        .enter().append("option")
        .attr("value", function(d) {return d})
        .property("selected", function(d) {return d == 'jet'})
        .text(function(d) {return d})
  }
  
  if (!(mychart && mychart.type && mychart.type == "heatmap_2d_multi")) {
    d3.selectAll("#plotdiv").selectAll("svg, div").remove();
    d3.select("#plotdiv").classed("plot", true);
    mychart = new heatChartMultiMasked(options, d3);
    var data = values[0];
    d3.selectAll("#plotdiv").data([values[0].datasets]).call(mychart);
    app.callbacks.resize_center = function() {mychart.autofit()};
  }
      
  var update_plotselect = function() {
    //d3.select(this).datum(parseInt(this.value));
    //console.log(d3.select(this), d3.select(this).datum(), this.value);
    var plotnum = (this && this.value != null) ? parseInt(this.value) : 0,
        data = values[plotnum];
    var title = data.title || "";
    d3.select("#plot_title").text(title);
    data.ztransform = $("#zscale").val();
    var aspect_ratio = null;
    if ((((data.options || {}).fixedAspect || {}).fixAspect || null) == true) {
      aspect_ratio = ((data.options || {}).fixedAspect || {}).aspectRatio || null;
    }
    
    mychart.options(data.options);
    //mychart = new heatChart();
    mychart
      //.ztransform($("#zscale").val())
      //.colormap(cm.get_colormap(current_instr == "NGBSANS" ? "spectral" : "jet"))
      //.autoscale(true)
      .aspect_ratio(aspect_ratio)
      //.dims(data.dims)
      .xlabel(data.xlabel)
      .ylabel(data.ylabel);
    //d3.selectAll("#plotdiv").selectAll("svg, div").remove();
    //d3.selectAll("#plotdiv").data(data.z).call(mychart);
    var new_colormap = get_colormap($("select#colormap_select").val(), d3);
    mychart.colormap(new_colormap);
    mychart.source_data(data.datasets);
    mychart.zoomScroll(true);
    mychart.ztransform($("#zscale").val())
    
    
  }
  
  d3.select("#plot_controls .plot-select input")
    .attr("max", values.length-1)
    .on("change", update_plotselect)
    .on("click", update_plotselect)
    .on("input", update_plotselect)
  
  mychart.interactors(null);
  update_plotselect.call(null);
  mychart.autofit();
  return mychart
}



function merge_1d_plotdata(plotdata) {
  var values = plotdata.values;
  var datas = [];
  var series = [];
  var xlabel, ylabel;
  values.forEach(function(v) {
    series = series.concat(v.options.series || [{}]);
    datas = datas.concat(v.data);
    if (v.options && v.options.axes) {
      if (v.options.axes.xaxis && v.options.axes.xaxis.label != null) {
        var new_xlabel = v.options.axes.xaxis.label;
        if (xlabel != null && xlabel != new_xlabel) {
          alert("inconsistent x-axis: " + xlabel + ", " + new_xlabel);
        }
        xlabel = new_xlabel;
      }
      if (v.options.axes.yaxis && v.options.axes.yaxis.label != null) {
        var new_ylabel = v.options.axes.yaxis.label;
        if (ylabel != null && ylabel != new_ylabel) {
          alert("inconsistent y-axis: " + ylabel + ", " + new_ylabel);
        }
        ylabel = new_ylabel;
      }
    }
  })
  var output = {
    options: {
      series: series,
      axes: {
        xaxis: {label: xlabel},
        yaxis: {label: ylabel}
      }
    },
    data: datas,
    type: "1d"
  }
  return output;
}

editor.show_plots_1d = function(plotdata) {
  var plotdata = merge_1d_plotdata(plotdata);
  var options = {
    series: [],
    legend: {show: true, left: 150},
    axes: {xaxis: {label: "x-axis"}, yaxis: {label: "y-axis"}}
  };
  extend(true, options, plotdata.options);
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
  var mychart = new xyChart(options, d3);
  d3.selectAll("#plotdiv").selectAll("svg, div").remove();
  d3.select("#plotdiv").classed("plot", true);
  d3.selectAll("#plotdiv").data([plotdata.data]).call(mychart);
  mychart.zoomRect(true);
  app.callbacks.resize_center = mychart.autofit;
  
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
          editor._active_plot[axis](transform);  
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
          editor._active_plot.options(o).update();
        });
        
    plot_controls
      .append("button")
        .attr("id", "export_data")
        .text("export")
        .on("click", editor.export_data)
    
    plot_controls
      .append("button")
        .attr("id", "download_svg")
        .html("get svg")
        .on("click", function() {
          var chart = webreduce.editor._active_plot;
          var svg = chart.export_svg();
          var serializer = new XMLSerializer();
          var output = serializer.serializeToString(svg);
          var filename = prompt("Save svg as:", "plot.svg");
          if (filename == null) {return} // cancelled
          download(output, filename);
        });
  }
  
  return mychart
}

editor.stash_data = function(suggested_name) {
  // embed the active template in a subroutine, exposing the
  // currently active output.  Store the structure in the 
  // browser.
  try {
      if (!window.localStorage) { throw false; }
  } catch (e) {
      alert("localStorage not supported in your browser");
      return;
  }
  if (editor._active_terminal == null) {
          alert("please select one input or output terminal to stash"); 
          return 
  }
  
  var suggested_name = (suggested_name == null) ?  "processed" : suggested_name;
  var stashname = prompt("stash data as:", suggested_name);
  if (stashname == null) {return} // cancelled
  
  var existing_stashes = _fetch_stashes();
  //var existing_stashnames = Object.keys(existing_stashes);
  
  if (existing_stashes.hasOwnProperty(stashname)) {
    var overwrite = confirm("stash named " + stashname + " already exists.  Overwrite?");
    if (!overwrite) {return}
  }
  
  var w = editor,
    node = w._active_node,
    terminal = w._active_terminal,
    template = w._active_template,
    instrument_id = w._instrument_id;
  var template_copy = extend(true, {}, template);
  var subroutine = {};
  subroutine.module = "user.stashed"
  subroutine.title = stashname;
  subroutine.module_def = {
    "template": template_copy,
    "inputs": [],
    "fields": [],
    "outputs": [{"source_module": node, "source_terminal": terminal, "terminal_id": "stashed"}],
    "action_id": "subroutine",
    "description": "previously processed data",
    "instrument_id": instrument_id
  }
  existing_stashes[stashname] = subroutine;
  _save_stashes(existing_stashes);
  editor.load_stashes(existing_stashes);
}

editor.load_stashes = function(stashes) {
  var existing_stashes = stashes || _fetch_stashes();
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

function _fetch_stashes() {
  try {
    return JSON.parse(localStorage['webreduce.editor.stashes'] || "{}");
  } catch (e) {
    return {}
  }
}
function _save_stashes(stashes) {
  try {
    localStorage['webreduce.editor.stashes'] = JSON.stringify(stashes);
  } catch (e) {}
}
function remove_stash(stashname) {
  var existing_stashes = _fetch_stashes();
  if (stashname in existing_stashes) {
    delete existing_stashes[stashname];
    _save_stashes(existing_stashes);
    editor.load_stashes();
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
    var instrument_id = stashed.module_def.instrument_id;
    editor.load_template(template, node, terminal, instrument_id);
  }
}

function compare_stashed(stashnames) {
  // stashnames is a list of stashed data ids
  // eventually send these as-is to server, but for now since the server
  // doesn't handle subroutines...
  d3.selectAll("g.module .selected").classed("selected", false);
  var existing_stashes = _fetch_stashes();
  var stashnames = stashnames.filter(function(s) {return (s in existing_stashes)});
  var recalc_mtimes = $("#auto_reload_mtimes").prop("checked");
  var params_to_calc = stashnames.map(function(stashname) {
    var stashed = existing_stashes[stashname];
    return {
      template: stashed.module_def.template,
      config: {},
      node: stashed.module_def.outputs[0].source_module,
      terminal: stashed.module_def.outputs[0].source_terminal,
      return_type: "plottable"
    }
  });
  return editor.calculate(params_to_calc, recalc_mtimes)
    .then(function(results) {
      if (results.length < 1) { return }
      var first = results[0];
      for (var i=1; i<results.length; i++) {
        if (results[i].datatype == first.datatype) {
          first.values = first.values.concat(results[i].values);
        }
      }
      editor.show_plots([first]);
    });
}

editor.get_versioned_template = function(template) {
  var versioned = extend(true, {}, template),
      editor = this,
      module_list = versioned.modules;
  module_list.forEach(function(m) {
    if (m.module && m.module in editor._module_defs) {
      m.version = editor._module_defs[m.module].version;
    }
  });
  return versioned
}

editor.get_cached_timestamps = function() {
  var cache = this._cache;
  return this._cache.allDocs({"include_docs": true})
    .then(function(res) {
      return res.rows.map(function(r) {return [r.doc.created_at, r.doc._id]})
    })
}

editor.get_signature = function(params) {
  var template = params.template,
      config = params.config || {},
      node = params.node,
      terminal = params.terminal,
      return_type = params.return_type || 'metadata',
      export_type = params.export_type || 'column',
      concatenate = params.concatenate || false;
  
  var versioned = this.get_versioned_template(template), 
      sig = sha1(JSON.stringify({
        method: "calculate",
        template: versioned,
        config: config,
        node: node,
        terminal: terminal,
        return_type: return_type, 
        export_type: export_type,
        concatenate: concatenate}));
        
  return sig
}

function calculate_one(params, caching) {
  var r = new Promise(function(resolve, reject) {resolve()});
  var template = params.template,
        config = params.config || {},
        node = params.node,
        terminal = params.terminal,
        return_type = params.return_type || 'metadata',
        export_type = params.export_type || 'column',
        concatenate = params.concatenate || false;
      
  if (caching) {
    var sig = editor.get_signature(params);
    r = r.then(function() { 
      return editor._cache.get(sig).then(function(cached) {return cached.value})
      .catch(function(e) {
        var versioned = editor.get_versioned_template(template);
        return server_api.calc_terminal({
            template_def: versioned,
            config: config,
            nodenum: node,
            terminal_id: terminal,
            return_type: return_type,
            export_type: export_type,
            concatenate: concatenate
          })
          .then(function(result) {
            var doc = {
              _id: sig, 
              created_at: Date.now(),
              value: result 
            }
            editor._cache.put(doc);
            return result
          })
          .catch(function(e) {
            console.log("error", e)
          })
      })
    })
  } else {
    r = r.then(function() { return server_api.calc_terminal({
      template_def: template,
      config: config,
      nodenum: node,
      terminal_id: terminal,
      return_type: return_type,
      export_type: export_type,
      concatenate: concatenate});
    })
    .catch(function(e) {
      console.log("error", e)
    });
  }
  return r
}

editor.calculate = function(params, recalc_mtimes, noblock, result_callback) {
  //var recalc_mtimes = $("#auto_reload_mtimes").prop("checked");
  // call result_callback on each result individually (this function will return all results
  // if you want to act on the aggregate after)
  var caching = $("#cache_calculations").prop("checked");
  var status_message = $("<div />");
  status_message.append($("<h1 />", {text: "Processing..."}));
  status_message.append($("<progress />"));
  status_message.append($("<span />"));
  status_message.append($("<button />", {text: "cancel", class: "cancel"}));
  
  editor._calculation_cancelled = false;
  var calculation_finished = false;
  var r = Promise.resolve();
  var cancel_promise = new Promise(function(resolve, reject) { 
    status_message.find("button").on("click", function() {
      editor._calculation_cancelled = true;
      calculation_finished = true;
      resolve({"cancelled": true})
    });
  });
  
  if (!noblock) {
    r = r.then(function() { 
      window.setTimeout(function() {
        if (!calculation_finished) {app.blockUI(status_message)}
        }, 200)
    })
  }
  if (recalc_mtimes) {
    r = r.then(function() { return Promise.race([cancel_promise, app.update_file_mtimes()])})
  }
  if (params instanceof Array) {
    var results = [],
        numcalcs = params.length;
    status_message.find("progress").attr("max", numcalcs.toFixed());
    params.forEach(function(p,i) {
      r = r.then(function() {
        if (editor._calculation_cancelled) {
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
    r = r.then(function(result) { calculation_finished = true; app.unblockUI(); return result; })
       .catch(function(err) { calculation_finished = true; app.unblockUI(); throw err });
  }
  return r;
}

var export_handlers = {
    
  download: function(result, filename) {
    if (result.values.length == 1) {
      download(result.values[0].value, filename);
    }
    else {
      var filect = 0;
      let subnames = new Set();
      let subcounter = 0;
      var write_next = function(writer, exports) {
        if (filect < exports.length) {
          var to_export = exports[filect++];
          let test_subname = to_export.filename || "default_filename";
          var subname = test_subname;
          while (subnames.has(subname)) {
            subname = test_subname + "_" + (subcounter++).toFixed();
          }
          subnames.add(subname);
          var reader = new zip.TextReader(to_export.value);
          writer.add(subname, reader, function() { write_next(writer, exports); });
        }
        else { 
          writer.close(function(blob) {
            download(blob, filename + ".zip");
          });
        }
      }
      return zip.createWriter(new zip.BlobWriter("application/zip"), function(writer) {
          write_next(writer, result.values);
        }, function(error) {
          console.log(error);
        });
    }
  },
    
  webapi: function(result, filename, data) {
      window.addEventListener("message", connection_callback, false);
      var connection_id = Math.random().toString(36).replace(/[^a-z]+/g, '').substr(0, 5);
      var webapp = window.open(data.url + "?connection_id=" + connection_id, "_blank");
      var exported = result.values.map(function(v) { return v.value }).join("\n\n");
      function connection_callback(event) {
        // hoisting is required... 
        var message = event.data;
        if (message.connection_id == connection_id) {
          window.removeEventListener("message", arguments.callee);
          if (message.ready) {
            webapp.postMessage({method: data.method, args: [exported], connection_id: connection_id}, "*");
          }
        }
      }
  }
}

editor.edit_categories = function() {
  if (!editor._datafiles[0]) {
    alert("no datafiles loaded");
    return
  }
  var instrument_id = editor._instrument_id;
  var categories = editor.instruments[instrument_id].categories;
  var dialog = $("div#categories_editor").dialog("open");
  var d3_handle = d3.select(dialog[0]);
  var list = d3_handle.select("ol.categories");
  $(list.node()).sortable();
  
  d3_handle.select("ol.add-more").selectAll("li.add-category").data([1])
    .enter().append("li").classed("add-category", true).style("list-style", "none")
    .append("span").classed("ui-icon ui-icon-circle-plus", true)
      .attr("title", "add category")
  d3_handle.select("ol.add-more").selectAll("li.add-category")
    .on("click", function() { 
      var new_data = [[]];
      var new_category = list.insert("li").data([new_data]).classed("category", true);
      add_selectors.call(new_category.node(), new_data);
    })
  
  
  function isObject(val) { return typeof val === 'object' && !Array.isArray(val)};
  function get_all_keys(obj) {
    var keys = Object.keys(obj);
    keys = keys.filter(function(k) { return !Array.isArray(obj[k]) });
    var output_keys = [];
    keys.forEach(function(k) {
      if (obj[k] && isObject(obj[k])) {
        output_keys.push([k, get_all_keys(obj[k])]);
      }
      else {
        output_keys.push([k]);
      }
    });
    return output_keys.sort();
  }
  
  var category_keys = get_all_keys(editor._datafiles[0]["values"][0]);
  
  function selector(c) {
    //c = c || {value: []};
    //c.value = c.value || [];
    var container = d3.create("span").classed("subcategory", true);
    var sel = container.append("select").classed("subcategory", true);
    sel.selectAll("option").data(c.choices)
      .enter().append("option")
        .attr("value", function(d) { return d[0] })
        .text(function(d) { return d[0] })
    function selection_change() {
      if (this.value != c.value[0]) {
        c.value[0] = this.value;
        c.value.splice(1);
      }
      container.selectAll("span").remove();
      var x = sel.selectAll('option[value="' + this.value + '"]');
      var cc = x.datum()[1];
      if (cc && cc.length) {
        c.value[1] = c.value[1] || [];
        container.selectAll("span.subcategory").data([{value: c.value[1], choices: cc}]).enter().append(selector);
      }
    }
    if (c.value && c.value[0]) {
      sel.property("value", c.value[0]);
    }
    sel.on("change", selection_change);
    selection_change.call(sel.node());
    return container.node()
  }
  
  
  function add_selectors(cl) {
    var citem = d3.select(this);
    var ccontainer = citem.append("span")
      .classed("category-container", true);
    var data = cl.map(function(c) { return {value: c, choices: category_keys.slice()}});
    ccontainer.selectAll("span.category").data(data)
      .enter().append("span").classed("category", true).append(selector)
    citem.append("span").classed("ui-icon ui-icon-circle-plus", true)
      .style("cursor", "pointer")
      .attr("title", "adding keywords on the same row makes a category from\nthe concatenation of the values with a colon (:) separator")
      .on("click", function() {
        cl.push([]);
        var data = cl.map(function(c) { return {value: c, choices: category_keys.slice()}});
        ccontainer.selectAll("span.category").data(data)
          .enter().append("span").classed("category", true)
          .append(selector)
      });
    citem.append("span").classed("ui-icon ui-icon-circle-close", true)
      .style("cursor", "pointer")
      .style("position", "absolute")
      .style("right", "0")
      .attr("title", "remove category")
      .on("click", function() { citem.remove() })
  }
  
  function set_data(categories) {
    list.selectAll("li.category").remove();
          
    var categories_nested = categories.map(function(cat) {
      return cat.map(function(v) { 
        return v.slice().reverse().reduce(function(a, s) { 
          var b = [s]; if (a) { b.push(a) }; return b; }, null)
      })
    });
    
    var citems = list.selectAll("li.category").data(categories_nested)
      .enter().append("li").classed("category", true)
        .style("border", "2px solid grey")
        .style("border-radius", "6px")
        .style("margin-bottom", "4px")
        .style("padding", "2px")
    
    citems.each(add_selectors);
  }
  
  set_data(categories);
  
  // button handlers
  d3_handle.select("button.apply").on("click", function() {
    var rawc = list.selectAll("li.category").data();
    function unpack(nested) {
      var unpacked = [];
      var residual = nested;
      while (residual && residual.length > 0) {
        unpacked.push(residual[0]);
        residual = residual.slice(1)[0];
      }
      return unpacked;
    }
    var unpacked = rawc.map(function(row) {
      return row.map(function(r) {
        return unpack(r) 
      })
    });
    editor.instruments[instrument_id].categories = unpacked;
    $("button#refresh_all").trigger("click");
  })
  d3_handle.select("button.close").on("click", function() { dialog.dialog("close"); });
  d3_handle.select("button.load-defaults").on("click", function() { 
    set_data(editor.instruments[instrument_id].default_categories);
  });
}

editor.export_targets = [
  { 
    "id": "download",
    "label": "download",
    "type": "download"
  }
];

editor.export_data = function() {
  var w = editor;
  if (w._active_terminal == null) { alert("no input or output selected to export"); }
  let active_modulename = w._active_template.modules[w._active_node].module;
  let active_module_def = editor._instrument_def.modules.find(function(m) { return m.id == active_modulename })
  let active_input_output = active_module_def.inputs
    .concat(active_module_def.outputs)
    .find(function(o) { return o.id == w._active_terminal});
  let export_datatype = active_input_output.datatype;

  var export_types = editor._instrument_def.datatypes.find(function(d) { return d.id == export_datatype}).export_types;
  var params = {
    template: w._active_template,
    config: {},
    node: w._active_node,
    terminal: w._active_terminal,
    return_type: "export",
    //export_type: export_type,
    concatenate: true
  }
  if (export_types.length == 0) {
    alert('no exports defined for this datatype: ' + export_datatype);
    return
  }
  /*
  else if (export_types.length == 1) {
    // if there's only one, no need to ask...
    params.export_type = export_types[0];
    initiate_export(params);
  }
  */
  else {
    // when there are more than one export types defined, ask which one to use:
    var export_dialog = $("div#initiate_export").dialog("open");
    var d3_handle = d3.select(export_dialog[0]);
    var export_type_choices = d3_handle.select("span#export_types").selectAll("label")
      .data(export_types, function(d) {return d})
    export_type_choices
      .enter().append("label")
        .text(function(d) { return d })
        .append("input")
          .attr("type", "radio")
          .property("checked", function(d,i) { return i==0 })
          .attr("name", "export_type_switcher")
          .attr("class", "custom-export")
          .attr("id", function(d) { return d })
    export_type_choices.exit().remove();

    d3_handle.select("button#export_cancel").on("click", function() { export_dialog.dialog("close"); });
    d3_handle.select("button#export_confirm").on("click", function() {
      export_dialog.dialog("close");
      var selected_export_type = d3_handle.select('input[name="export_type_switcher"]:checked');
      let export_type = selected_export_type.attr("id");
      let concatenate = d3_handle.select('input#concatenate_exports').property("checked");
      params.export_type = export_type;
      params.concatenate = concatenate;
      initiate_export(params);
    });
  }

}

function initiate_export(params) {
  var w = editor;
  var recalc_mtimes = $("#auto_reload_mtimes").prop("checked");
  editor.calculate(params, recalc_mtimes).then(function(result) {
    // add the template and target node, terminal to the header of the file:
    var suggested_name = (result.values[0] || {}).filename || "myfile.refl";
    var additional_export_targets = editor.instruments[w._instrument_id].export_targets || [];
    var dialog = $("div#route_export_data").dialog("open");
    var d3_handle = d3.select(dialog[0]);
    //d3_handle.selectAll("span#export_targets label").remove();
    var export_targets = editor.export_targets.concat(additional_export_targets);
    var route_choices = d3_handle.select("span#export_targets").selectAll("label")
      .data(export_targets, function(d,i) { return w._instrument_id + d.id; })
    route_choices
      .enter().append("label")
        .text(function(d) { return d.label })
        .append("input")
          .attr("type", "radio")
          .property("checked", function(d,i) { return i==0 })
          .attr("data-handler", function(d) { return d.type })
          .attr("name", "export_switcher")
          .attr("class", "custom-export")
          .attr("id", function(d) { return d.id })
    route_choices.exit().remove();
      
    d3_handle.select("input#export_filename").property("value", suggested_name);
    d3_handle.select("button#export_cancel").on("click", function() { dialog.dialog("close"); });
    d3_handle.select("button#export_confirm").on("click", function() {
      dialog.dialog("close");
      var filename = d3_handle.select("input#export_filename").node().value;
      var selected_exporter = d3_handle.select('input[name="export_switcher"]:checked')
      var handler = selected_exporter.attr("data-handler");
      var data = (selected_exporter.datum) ? selected_exporter.datum() : {};
      export_handlers[handler](result, filename, data);
    });
  });
}

editor.accept_parameters = function(target, active_module) {
  target.selectAll("div.fields")
    .each(function(data) {
      if (typeof data.value !== "undefined") {
        if (!active_module.config) {active_module.config = {}};
        active_module.config[data.id] = data.value;
      }
    });
  editor.update_completions();
}

editor.update_completions = function() {
  var satisfactions = dependencies.mark_satisfied(this._active_template, this._module_defs);
  var wires = this._active_template.wires;
  var svg = this._instance.svg();
  svg.selectAll("path.wire").classed("filled", function(d,i) { return satisfactions.wires_satisfied.has(i); });
  svg.selectAll("g.module").each(function(d,i) {
    d3.select(this).selectAll("rect.terminal.output").style("fill", (satisfactions.modules_satisfied.has(i)) ? null : "url(#output_hatch)");
  })
  svg.selectAll("rect.terminal.input").style("fill", "url(#input_hatch)");
  svg.selectAll("rect.terminal.input").each(function(d,i) {
    var term = d3.select(this);
    var id = term.attr("terminal_id");
    var node = d3.select(this.parentNode.parentNode).attr("index");
    wires.forEach(function(w,i) { 
      var mine = (w.target[0] == node && w.target[1] == id);
      if (mine && satisfactions.wires_satisfied.has(i)) {
        term.style("fill", null);
      }
    });
  });
}

editor.fileinfo_update = function(fileinfo) {
  filebrowser.fileinfoUpdate(fileinfo);
}

editor.load_instrument = function(instrument_id) {
  var editor = this;
  editor._instrument_id = instrument_id;
  return server_api.get_instrument({instrument_id: instrument_id})
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

editor.switch_instrument = function(instrument_id, load_default) {
  // load_default_template is a boolean: true if you want to do that action
  // (defaults to true)
  var load_default = (load_default == null) ? true : load_default;
  if (instrument_id == editor._instrument_id) {
    // then there's nothing to do...
    return Promise.resolve();
  }
  return this.load_instrument(instrument_id)
    .then(function(instrument_def) { 
        var template_names = Object.keys(instrument_def.templates);
        $("#main_menu #predefined_templates ul").empty();
        template_names.forEach(function (t,i) {
          $("#main_menu #predefined_templates ul").append($("<li />").append($("<div />", {text: t})));
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
        if (load_default) {
          app.current_instrument = instrument_id;
          var template_copy = extend(true, {}, instrument_def.templates[default_template]);
          return editor.load_template(template_copy);
        } else {
          return 
        }
      });
}

editor.edit_template = function(template_def, instrument_id) {
  var template_def = template_def || this._active_template;
  var instrument_id = instrument_id || this._instrument_id;
  var post_load = function() {
    var te = editor._active_template_editor;
    te.load_instrument(instrument_id)
        .then(function(){
          te.e.import(template_def, true);
          te.e.add_brush();
        })
    d3.select(te.document.getElementById("apply_changes")).on('click', function() {
      editor.load_template(te.e.export(), null, null, instrument_id);
    });
  }
  if (this._active_template_editor == null || this._active_template_editor.closed) {
    var te = window.open(template_editor_url, "template_editor", "width=960,height=480");
    this._active_template_editor = te;
    te.addEventListener('editor_ready', post_load, false);
  }
}

editor.load_template = function(template_def, selected_module, selected_terminal, instrument_id) {
  var we = this;
  var instrument_id = instrument_id || we._instrument_id;
  var r = we.switch_instrument(instrument_id, false).then(function() {
      
    we._active_template = template_def;
    var template_sourcepaths = filebrowser.getAllTemplateSourcePaths(template_def),
        browser_sourcepaths = filebrowser.getAllBrowserSourcePaths();
    var sources_loaded = Promise.resolve();
    for (var source in template_sourcepaths) {
      var paths = Object.keys(template_sourcepaths[source]);
      paths.forEach(function(path,i) {
        if (browser_sourcepaths.findIndex(function(sp) {return sp.source == source && sp.path == path}) < 0) {
          sources_loaded = sources_loaded.then(function() {
            return filebrowser.addDataSource(source, path.split("/"));
          });
        }
      });
    }
    
    var target = d3.select("#" + we._target_id);    
    we._instance.import(template_def);

    target.selectAll(".module").classed("draggable wireable", false);
    target.selectAll("g.module").on("click", editor.handle_module_clicked);
    //target.selectAll("g.module").on("contextmenu", editor.handle_module_contextmenu);
    
    var autoselected = template_def.modules.findIndex(function(m) {
      var has_fileinfo = editor._module_defs[m.module].fields
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
      
      sources_loaded = sources_loaded.then(function() {
        return editor.handle_module_clicked.call(toselect.node(), toselect.datum(), autoselected, null, toselect_target); 
      }).then(function() {
        return editor.update_completions();
      });
    }
    app.autoselected = autoselected;
    return
  });
  return r;
  
}

editor.load_metadata = async function(files_metadata, datasource, path) {
  var instrument_id = editor._instrument_id;
  var instrument = editor.instruments[instrument_id];
  var file_objs = {};
  var files_filter = instrument.files_filter || function(x) {return true};
  var files = Object.keys(files_metadata);
  var datafiles = files.filter(files_filter);

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

  let loader_template = instrument.load_file(load_params, file_objs, false, 'metadata');
  let results = await editor.calculate(loader_template, false, false);
  results.forEach(function(result, i) {
    var lp = load_params[i];
    if (result && result.values) {
      result.values.forEach(function(v) {v.mtime = lp.mtime});
      file_objs[lp.path] = result;
    }
  });
  
  editor._datafiles = results;
  return file_objs;
}