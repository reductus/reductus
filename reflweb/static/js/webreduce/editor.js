// require(d3.js, webreduce.server_api, dataflow)
// require(d3, dataflow)

webreduce.editor = webreduce.editor || {};

(function () {
	webreduce.editor.dispatch = d3.dispatch("accept");
	
  webreduce.editor.create_instance = function(target_id) {
    // create an instance of the dataflow editor in
    // the html element referenced by target_id
    this._instance = new dataflow.editor();
    this._target_id = target_id;
  }
  webreduce.editor.handle_module_clicked = function() {
    // module group is 2 levels above module title in DOM
    webreduce.editor.dispatch.on("accept", null);
    var target = d3.select("#" + this._target_id);
    var index = d3.select(target.select(".module .selected").node().parentNode.parentNode).attr("index");
    var active_module = this._active_template.modules[index];
    var module_def = this._module_defs[active_module.module];
    var fields = module_def.fields || [];
    var fields_dict = {};
    fields.forEach(function(f) {
      fields_dict[f.id] = f.default}
    );
    jQuery.extend(true, fields_dict, active_module.config);
    webreduce.layout.open("east");
    var target = d3.select(".ui-layout-pane-east");
    target.selectAll("div").remove();
    webreduce.editor.make_form(fields, active_module);
    webreduce.editor.handle_fileinfo(fields, active_module);
    webreduce.editor.handle_indexlist(fields, this._active_template, index)

    target.append("div")
      .style("position", "absolute")
      .style("bottom", "0")
      .append("button")
        .text("accept")
        .on("click", function() {
          console.log(target, active_module);
          webreduce.editor.accept_parameters(target, active_module);
          webreduce.editor.handle_module_clicked();
        })
  }
  
  webreduce.editor.handle_terminal_clicked = function() {
    var target = d3.select("#" + this._target_id);
    var selected = target.select(".module .selected");
    var index = parseInt(d3.select(selected.node().parentNode.parentNode).attr("index"));
    var terminal_id = selected.attr("terminal_id");
    webreduce.server_api.calc_terminal(this._active_template, {}, index, terminal_id).then(function(result) {
      webreduce.editor.show_plots(result.values);      
    }); 
  }
  
  webreduce.editor.show_plots = function(values) {
    var instrument_id = this._instrument_id;
    var options={series: [], axes: {xaxis: {label: "x-axis"}, yaxis: {label: "y-axis"}}};
    var new_plotdata = webreduce.instruments[instrument_id].plot(values);
    options.series = options.series.concat(new_plotdata.series);
    var datas = new_plotdata.data;
    var xlabel = new_plotdata.xlabel;
    var ylabel = new_plotdata.ylabel;
    options.legend = {"show": true, "left": 125};
    options.axes.xaxis.label = xlabel;
    options.axes.yaxis.label = ylabel;
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
    //$("#xscale, #yscale").change(handleChecked);
    mychart.zoomRect(true);
  }

  webreduce.editor.accept_parameters = function(target, active_module) {
    target.selectAll("div.fields")
      .each(function(d) {
        console.log(d)
        d.forEach(function(data) {
          if (!active_module.config) {active_module.config = {}};
          active_module.config[data.id] = data.value;
        });
      });
  }
  
  webreduce.editor.handle_fileinfo = function(fields, active_module) {
    var fileinfos = fields.filter(function(f) {return f.datatype == 'fileinfo'});
    var target = d3.select(".ui-layout-pane-east");
    target.append("div")
      .attr("id", "fileinfo")
      //.classed("fields", true);
      
    fileinfos.forEach(function(fi) {
      var datum = {"id": fi.id, value: []},
          existing_count = 0;
      if (active_module.config && active_module.config[fi.id] ) {
        existing_count = active_module.config[fi.id].length;
        datum.value = active_module.config[fi.id];
      }
      var radio = target.select("#fileinfo").append("div")
        .classed("fields", true)
        .datum([datum])
      radio.append("input")
        .attr("id", fi.id)
        .attr("type", "radio")
        .attr("name", "fileinfo");
      radio.append("label")
        .attr("for", fi.id)
        .text(fi.id + "(" + existing_count + ")");
        
      $(radio.node()).on("fileinfo.update", function(ev, info) {
        if (radio.select("input").property("checked")) {
            radio.datum([{id: fi.id, value: info}]);
        } 
      });

    });
    $("#fileinfo input").first().prop("checked", true);
    $("#fileinfo input").on("click", function() {
      //console.log(d3.select(this).datum());
      $(".remote_filebrowser").trigger("fileinfo.update", d3.select(this).datum());
    })
    $("#fileinfo").buttonset();
    webreduce.handleChecked(); // to populate the datum
  }
  
  webreduce.editor.handle_indexlist = function(fields, active_template, module_index) {
    var indexlists = fields.filter(function(f) {return f.datatype == 'index'});
    var target = d3.select(".ui-layout-pane-east");
    var active_module = active_template[module_index];
    var input_id = "data"
    indexlists.forEach(function(il) {
      var inputs = active_template.wires.filter(function(w) {return (w.target[0] == module_index && w.target[1] == input_id)});
      console.log(inputs, il, module_index);
      var data_promises = [];
      inputs.forEach(function(wire) {
        var input_module = wire.source[0],
            terminal_id = wire.source[1];
        data_promises.push(webreduce.server_api.calc_terminal(active_template, {}, input_module, terminal_id));
      });
      Promise.all(data_promises).then(function(results) {
        console.log('data to mask:', results);
        var datasets = [];
        results.forEach(function(r) {datasets = datasets.concat(r.values)});
        // now have a list of datasets.
        var index_lists = [];
        datasets.forEach(function(d,i) {index_lists[i] = []});
        webreduce.editor.show_plots(datasets);
        d3.selectAll("#plotdiv .dot").on("click", null); // clear previous handlers
        d3.selectAll("#plotdiv svg g.series").each(function(d,i) {
          // i is index of dataset
          d3.select(this).selectAll(".dot").on("click", function(dd, ii) {
            // ii is the index of the point in that dataset.
            var index_list = index_lists[i];
            var index_index = index_list.indexOf(ii);
            if (index_index > -1) { index_list.splice(index_index, 1); d3.select(this).classed("masked", false); }
            else {index_list.push(ii); d3.select(this).classed("masked", true);}
            console.log(JSON.stringify(index_lists));
          });
        });
      });
    });

    
  }
  
  webreduce.editor.fileinfo_update = function(fileinfo) {
    $(".remote_filebrowser").trigger("fileinfo.update", [fileinfo]);
  }

  webreduce.editor.make_form = function(fields, active_module) {
    var data = [];
    var conversions = {
      'bool': 'checkbox',
      'int': 'number',
      'float': 'number',
      'str': 'text'
    }
    for (var i=0; i<fields.length; i++) {
      var field = fields[i];
      var dt = field.datatype.split(":"),
          datatype = dt[0],
          units = dt[1];
      if (units === "") {units = "unitless"}
      if (datatype in conversions) {
        var value = (active_module.config && field.id in active_module.config)? active_module.config[field.id] : field.default;
        data.push({
          'type': conversions[field.datatype],
          'value': value,
          'label': field.label + ((units === undefined) ? "" : "(" + units + ")"),
          'id': field.id
        });
      }
    }

    var target = d3.select(".ui-layout-pane-east");
    target.selectAll("div").remove();
    //var forms = target.select("div.form")
    //.data([data]).enter()
    var forms = target.append("div")
      .classed("form fields", true)
      .style("list-style", "none");
    forms.datum(data);
    
    forms.selectAll("li")
      .data(function(d) {return d})
      .enter()
      .append("li")
      .append("label")
      .text(function(d) {return d.label})
      .append("input")
      .attr("type", function(d) {return d.type})
      .attr("field_id", function(d) {return d.id})
      .attr("value", function(d) {return d.value})
      .property("checked", function(d) {return d.value})
      .on("change", function(d) {
        var item = d3.select(this);
        if (this.type == "checkbox") { d.value = this.checked }
        else { d.value = this.value }
      });
    
    //$(forms.node()).on("accept", function() {
    /*webreduce.editor.dispatch.on("accept.form", function() {
      active_module.config = active_module.config || {};
      forms.selectAll("li")
      .each(function() {
        var item = d3.select(this).select("input");
        var value = (item.attr("type") == "checkbox") ? item.property("checked") : item.attr("value");
        var field_id = item.attr("field_id");
        active_module.config[field_id] = value;
      })
    });
    */
      //  alert("accepting fields");
      //  active_module.config = active_module.config || {};
      //  active_module.config[d3.select(this).attr('field_id')] = this.value;
      //})
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
  
  webreduce.editor.load_template = function(template_def) {
    this._instance.data([template_def]);
    this._active_template = template_def;
    var target = d3.select("#" + this._target_id);

    target.call(this._instance);

    target.selectAll(".module").classed("draggable wireable", false);

    target.selectAll(".module .terminal").on("click", function() {
      target.selectAll(".module .selected").classed("selected", false);
      d3.select(this).classed('selected', true);
      webreduce.editor.handle_terminal_clicked();
    });
    target.selectAll(".module g.title").on("click", function() {
      target.selectAll(".module .selected").classed("selected", false);
      d3.select(this).select("rect.title").classed("selected", true);
      webreduce.editor.handle_module_clicked();
    });
  }
  
  
})();
