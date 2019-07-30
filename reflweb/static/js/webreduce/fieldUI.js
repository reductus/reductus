var webreduce = webreduce || {};
webreduce.editor = webreduce.editor || {};
webreduce.editor.make_fieldUI = webreduce.editor.make_fieldUI || {};

(function(fieldUI){
  var fileinfoUI = function() {
    // call with context defined:
    var datum = this.datum,
        field = this.field,
        target = this.target,
        datasets_in = this.datasets_in,
        module = this.active_module;

    $("#datasources .block-overlay").hide();
    if (target.select("div#fileinfo").empty()) {
      target.append("div")
        .attr("id", "fileinfo")
    }

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
      .append("span")
        .classed("fileinfo-label", true)
        .text(field.id + "(" + existing_count + ")");
    
    // jquery events handler for communications  
    $(radio.node()).on("fileinfo.update", function(ev, info) {
      if (radio.select("input").property("checked")) {
          radio.datum({id: field.id, value: info});
          radio.select("label span.fileinfo-label").text(field.id + "(" + info.length + ")");
          // auto-accept fileinfo clicks.
          webreduce.editor.accept_parameters(target, module);
      }
    });

    target.select("#fileinfo input").property("checked", true); // first one
    target.selectAll("div#fileinfo input")
      .on("click", function() {
        $(".remote-filebrowser").trigger("fileinfo.update", d3.select(this).datum());
      });
    $("#fileinfo").buttonset();
    $(".remote-filebrowser").trigger("fileinfo.update", d3.select("div#fileinfo input").datum());
    // if there is data loaded, an output terminal is selected... and will be plotted instead
    if (datasets_in == null) { webreduce.handleChecked(null, null, true) };
    return radio
  }
  fieldUI.fileinfo = fileinfoUI;
  
  var indexUI = function() {
    var datum_in = this.datum,
        field = this.field,
        target = this.target,
        datasets_in = this.datasets_in,
        module = this.active_module;
  
    if (target.select("div#indexlist").empty()) {
      target.append("div")
        .attr("id", "indexlist")
    }
    
    var datasets = datasets_in.values;
    // now have a list of datasets.
    var datum = jQuery.extend(true, {}, datum_in);
    datum.value = datum.value || datum.default_value;
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
        datum.value = JSON.parse(this.value)
      });
    
    // add interactors:
    if (this.add_interactors) {
      var active_plot = this.active_plot;
      var drag_instance = d3.drag();
      active_plot.svg.call(drag_instance);
      var selector = new rectangleSelect.default(drag_instance);
      active_plot.interactors(selector);
      var select_active = true;
      var zoom_active = true; // overrides select_active...
      
      var onselect = function(xmin, xmax, ymin, ymax) {
        if (zoom_active) {
          active_plot.x().domain([xmin, xmax]);
          active_plot.y().domain([ymin, ymax]);
          active_plot.update();
        }
        else {  
          d3.selectAll("#plotdiv svg g.series").each(function(d,i) {
            // i is index of dataset
            var series_select = d3.select(this);
            if (series_select.classed("hidden")) {
              // don't interact with hidden series.
              return
            }
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
          var event = document.createEvent('Event');
          event.initEvent('input', true, true);
          input.node().dispatchEvent(event);
        }
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
      
      select_select
        .append("label")
        .text("select")
        .append("input")
        .attr("name", "select_select")
        .attr("type", "radio")
        .attr("value", "select")
        .property("checked", true)
        
      select_select
        .append("label")
        .text("deselect")
        .append("input")
        .attr("name", "select_select")
        .attr("type", "radio")
        .attr("value", "deselect")

      var selectorchange = function(ev) {
        if (this.value == 'zoom') {
          zoom_active = true;
        }
        else if (this.value == 'select') {
          zoom_active = false;
          select_active = true;
        }
        else if (this.value == 'deselect') {
          zoom_active = false;
          select_active = false;
        }
      }
      
      select_select.selectAll("input").on("change", selectorchange);
      selectorchange.call({value: "select"});
    
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
      
      input.on("change", function(d) {
        datum.value = JSON.parse(this.value);
        update_plot();
      });
      
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
          input.text(prettyJSON(datum.value));
          var event = document.createEvent('Event');
          event.initEvent('input', true, true);
          input.node().dispatchEvent(event);
        });
      });
    }
    return input;
  }
  fieldUI.index = indexUI;
  
  var scaleUI = function() {
    var datum = this.datum,
        field = this.field,
        target = this.target,
        datasets_in = this.datasets_in,
        module = this.active_module;
        
  
    target.selectAll("div#scalelist").data([0])
      .enter()
        .append("div")
        .attr("id", "scalelist")
    
    var datasets = datasets_in.values;
    var value = (datum.value == null) ? datum.default_value : datum.value;
    // now have a list of datasets.
    datum.value = value.slice(0,datasets.length);
    datasets.forEach(function(d,i) {
      datum.value[i] = (datum.value[i] == null) ? 1 : datum.value[i];
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
    
    if (this.add_interactors) {
      var active_plot = this.active_plot;
      d3.selectAll("#plotdiv .dot").on("click", null); // clear previous handlers
      d3.selectAll("#plotdiv svg g.series").each(function(d,i) {
        // i is index of dataset
        // make a copy of the data:
        unscaled_data[i] = $.extend(true, [], d);
        var new_scale = datum.value[i];
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
        var dragmove_point = function(dd,ii) {
          var chart = active_plot;
          var y = chart.y(),
              x = chart.x();
          var new_x = x.invert(d3.event.x),
            new_y = chart.y().invert(d3.event.y),
            old_point = unscaled_data[i][ii],
            old_x = old_point[0],
            old_y = old_point[1];
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
          datum.value[i] = new_scale; // * original_datum[i];
          input.text(JSON.stringify(datum.value, null, 2));
          var event = document.createEvent('Event');
          event.initEvent('input', true, true);
          input.node().dispatchEvent(event);
          chart.update();
        }
        var drag_point = d3.drag()
          .on("drag", dragmove_point)
          .on("start", function() { d3.event.sourceEvent.stopPropagation(); });
        var series_select = d3.select(this);
        series_select.selectAll(".dot")
          .attr("r", 7) // bigger for easier drag...
          .call(drag_point)
      });
      active_plot.do_autoscale();
      active_plot.resetzoom();
    }
    return input;
  }
  
  fieldUI.scale = scaleUI;
  //function(field, active_template, datum, module_def, target, datasets_in) {

  var rangeUI = function() {
    var datum = this.datum,
        field = this.field,
        axis = this.field.typeattr['axis'] || "?",
        target = this.target,
        datasets_in = this.datasets_in,
        module = this.active_module;
    
    target.append("div").append("label").text(field.label);
    var input = target.append("div")
      .classed("fields", true)
      .datum(datum)
    
    var subfields = []
      .concat((/x/.test(axis)) ? ["xmin", "xmax"] : [])
      .concat((/y/.test(axis)) ? ["ymin", "ymax"] : [])
      .concat((/^ellipse$/.test(axis)) ? ["cx", "cy", "rx", "ry"] : [])
      .concat((/^sector_centered$/.test(axis)) ? ["angle_offset", "angle_width"] : []);

    var subinputs = input.selectAll("div.subfield").data(subfields).enter()
      .append("div")
      .classed("subfield", true)
      .append("label")
      .text(function(d) {return d})
        .append("input")
          .attr("type", "text")
          .attr("placeholder", function(d,i) { return (datum.default_value || [])[i] })
          .on("change", function(d,i) { 
            if (datum.value == null) { datum.value = datum.default_value }
            datum.value[i] = parseFloat(this.value);
          });
    subinputs
      .attr("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
      .property("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
          
    if (this.add_interactors) {
      var active_plot = this.active_plot;
      if (axis == 'x' && active_plot &&  active_plot.interactors) {
        // add x-range interactor
        var xrange = active_plot.x().domain();
        var value = datum.value || datum.default_value;
        var value = [
          (value[0] == null) ? xrange[0] : value[0],
          (value[1] == null) ? xrange[1] : value[1]
        ]
        var opts = {
          type: 'xrange',
          name: 'xrange',
          color1: 'blue',
          show_lines: true,
          x1: value[0],
          x2: value[1]
        }
        var interactor = new xSliceInteractor.default(opts);
        active_plot.interactors(interactor);
        subinputs.on("change", function(d,i) { 
          if (datum.value == null) { datum.value = datum.default_value }
          var v = parseFloat(this.value);
          v = (isNaN(v)) ? null : v;
          datum.value[i] = v;
          var xitem = ["x1", "x2"][i];
          interactor.state[xitem] = (v == null) ? xrange[i] : v;
          interactor.update(false);
        });
        interactor.dispatch.on("update", function() { 
          var state = interactor.state;
          datum.value = [state.x1, state.x2];
          subinputs
            .property("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
            .attr("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
          var event = document.createEvent('Event');
          event.initEvent('input', true, true);
          subinputs.node().dispatchEvent(event);
        });
        
      }
      else if (axis == 'y' && active_plot &&  active_plot.interactors) {
        // add y-range interactor
        var yrange = active_plot.y().domain();
        var value = datum.value || datum.default_value;
        var value = [
          (value[0] == null) ? yrange[0] : value[0],
          (value[1] == null) ? yrange[1] : value[1]
        ]
        var opts = {
          type: 'yrange',
          name: 'yrange',
          color1: 'green',
          show_lines: true,
          y1: value[0],
          y2: value[1]
        }
        var interactor = new ySliceInteractor.default(opts);
        active_plot.interactors(interactor);
        subinputs.on("change", function(d,i) { 
          if (datum.value == null) { datum.value = datum.default_value }
          var v = parseFloat(this.value);
          v = (isNaN(v)) ? null : v;
          datum.value[i] = v;
          var yitem = ["y1", "y2"][i];
          interactor.state[yitem] = (v == null) ? yrange[i] : v;
          interactor.update(false);
        });
        interactor.dispatch.on("update", function() { 
          var state = interactor.state;
          datum.value = [state.y1, state.y2];
          subinputs
            .property("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
            .attr("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
          var event = document.createEvent('Event');
          event.initEvent('input', true, true);
          subinputs.node().dispatchEvent(event);
        });
      }
      else if (axis == 'xy' && active_plot && active_plot.interactors) {
        // add box interactor
        var xrange = active_plot.x().domain(),
            yrange = active_plot.y().domain();
        var value = datum.value || datum.default_value;
        var value = [
          (value[0] == null) ? xrange[0] : value[0],
          (value[1] == null) ? xrange[1] : value[1],
          (value[2] == null) ? yrange[0] : value[2],
          (value[3] == null) ? yrange[1] : value[3]
        ]
        
        var opts = {
          type: 'Rectangle',
          name: 'range',
          color1: 'red',
          color2: 'LightRed',
          fill: "none",
          show_center: false,
          xmin: value[0],
          xmax: value[1],
          ymin: value[2], 
          ymax: value[3]
        }
        var interactor = new rectangleInteractor.default(opts);
        active_plot.interactors(interactor);
        // bind the update after init, so that it doesn't alter the field at init.
        subinputs.on("change", function(d,i) { 
          if (datum.value == null) { datum.value = datum.default_value }
          var v = parseFloat(this.value);
          v = (isNaN(v)) ? null : v;
          datum.value[i] = v;
          var item = ["xmin", "xmax", "ymin", "ymax"][i];
          var default_value = (i<2) ? xrange[i] : yrange[i-2];
          interactor.state[item] = (v == null) ? default_value : v;
          interactor.update(false);
        });
        interactor.dispatch.on("update", function() { 
          var state = interactor.state;
          datum.value = [state.xmin, state.xmax, state.ymin, state.ymax];
          subinputs
            .property("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
            .attr("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
          var event = document.createEvent('Event');
          event.initEvent('input', true, true);
          subinputs.node().dispatchEvent(event);
        });
      }
      else if (axis == 'ellipse' && active_plot && active_plot.interactors) {
        // add ellipse interactor
        var xrange = active_plot.x().domain(),
            yrange = active_plot.y().domain();
        var value = datum.value || datum.default_value;
        var value = [
          (value[0] == null) ? (xrange[0] + xrange[1])/2 : value[0],
          (value[1] == null) ? (yrange[0] + yrange[1])/2 : value[1],
          (value[2] == null) ? (xrange[0] + xrange[1])/2 : value[2],
          (value[3] == null) ? (yrange[0] + yrange[1])/2 : value[3]
        ]
        
        var opts = {
          type: 'Ellipse',
          name: 'range',
          color1: 'red',
          color2: 'LightRed',
          fill: "none",
          show_center: true,
          show_points: true,
          cx: value[0],
          cy: value[1],
          rx: value[2], 
          ry: value[3]
        }
        var interactor = new ellipseInteractor.default(opts);
        active_plot.interactors(interactor);
        // bind the update after init, so that it doesn't alter the field at init.
        subinputs.on("change", function(d,i) { 
          if (datum.value == null) { datum.value = datum.default_value }
          var v = parseFloat(this.value);
          v = (isNaN(v)) ? null : v;
          datum.value[i] = v;
          var item = ["cx", "cy", "rx", "ry"][i];
          var default_value = (i == 0 || i == 2) ? (xrange[0] + xrange[1])/2 : (yrange[0] + yrange[1])/2;
          interactor.state[item] = (v == null) ? default_value : v;
          interactor.update(false);
        });
        interactor.dispatch.on("update", function() { 
          var state = interactor.state;
          datum.value = [state.cx, state.cy, state.rx, state.ry];
          subinputs
            .property("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
            .attr("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
          var event = document.createEvent('Event');
          event.initEvent('input', true, true);
          subinputs.node().dispatchEvent(event);
        });
      }
      else if (axis == 'sector_centered' && active_plot && active_plot.interactors) {
        // add angleSlice interactor
        var value = datum.value || datum.default_value;
        var value = [
          (value[0] == null) ? 0.0 : value[0],
          (value[1] == null) ? 90.0 : value[1]
        ]
        
        var opts = {
          type: 'Sector',
          name: 'sector',
          color1: 'red',
          color2: 'orange',
          show_lines: true,
          show_center: false,
          mirror: true,
          cx: 0,
          cy: 0,
          angle_offset: value[0] * Math.PI/180.0,
          angle_range: value[1] * Math.PI/180.0
        }

        var interactor = new angleSliceInteractor.default(opts);
        active_plot.interactors(interactor);
        // bind the update after init, so that it doesn't alter the field at init.
        subinputs.on("change", function(d,i) { 
          if (datum.value == null) { datum.value = datum.default_value }
          var v = parseFloat(this.value);
          v = (isNaN(v)) ? null : v;
          datum.value[i] = v;
          var item = ["angle_offset", "angle_range"][i];
          var default_value = [0.0, Math.PI/2.0][i];
          interactor.state[item] = (v == null) ? default_value : v * Math.PI/180.0;
          interactor.update(false);
        });
        interactor.dispatch.on("update", function() { 
          var state = interactor.state;
          datum.value = [state.angle_offset * 180.0/Math.PI, state.angle_range * 180.0/Math.PI];
          subinputs
            .property("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
            .attr("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
          var event = document.createEvent('Event');
          event.initEvent('input', true, true);
          subinputs.node().dispatchEvent(event);
        });
      } 
    }
    return input    
  }
  fieldUI.range = rangeUI;
  
  var coordinateUI = function() {
    var datum = this.datum,
        field = this.field,
        axis = this.field.typeattr['axis'] || "?",
        target = this.target,
        datasets_in = this.datasets_in,
        module = this.active_module;
    
    target.append("div").append("label").text(field.label);
    var input = target.append("div")
      .classed("fields", true)
      .datum(datum)
    
    var subfields = ["x", "y"];
    var subinputs = input.selectAll("div.subfield").data(subfields).enter()
      .append("div")
      .classed("subfield", true)
      .append("label")
      .text(function(d) {return d})
        .append("input")
          .attr("type", "text")
          .attr("placeholder", function(d,i) { return (datum.default_value || [])[i] })
          .on("change", function(d,i) { 
            if (datum.value == null) { datum.value = datum.default_value }
            datum.value[i] = parseFloat(this.value);
          });
    subinputs
      .attr("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
      .property("value", function(d,i) { return (datum.value) ? datum.value[i] : null })
      
    return input;
  }
  fieldUI.coordinate = coordinateUI;
  
  var patchUI = function() {
    var datum = this.datum,
        field = this.field,
        target = this.target,
        datasets_in = this.datasets_in,
        module = this.active_module;
    
    let key = field.typeattr.key;

    datum.value = datum.value || [];
    var input = target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("ul")
        .classed("metadata-patches", true)
    
    input.append("div")
      .classed("patch_key", true)
      .text("Key: " + field.typeattr.key)

    input.selectAll("li.patches").data(datum.value).enter()
      .append("li")
      .classed("patches", true)
    
    input.selectAll("li.patches")
      .text(function(d) { return JSON.stringify(d)})

    var op = "replace";

    if (this.add_interactors) {
      var active_plot = this.active_plot;
      cols = active_plot.selectAll("th.colHeader").data();
      key_col = cols.indexOf(key);
      active_plot.selectAll(".metadata-row")
        .each(function(d,i) { 

          d3.select(this).selectAll("pre")
            .attr("contenteditable", function(dd, ii) {
              return ii != key_col;
            })
            .attr("title", function(dd, ii) {
              let c = cols[ii];
              return "was: " + d[c];
            })
            .on("input", function(dd, ii) {
              let c = cols[ii];
              let new_text = this.innerText;
              let old_text = String(d[c]);
              let dirty = (old_text != new_text);
              d3.select(this.parentNode).classed("dirty", dirty);
              let path = "/" + d[key] + "/" + c;
              var p = {path: path, value: new_text, op: op}
              let update_existing = false;
              if (dirty) {
                for (var po of datum.value) {
                  if (po.path == path) {
                    po.value = new_text;
                    update_existing = true;
                    break;
                  }
                }
                if (!update_existing) {
                  datum.value.push(p);
                }
              }
              else {
                for (var vi in datum.value) {
                  let po = datum.value[vi];
                  if (po.path == path) {
                    datum.value.splice(vi, 1);
                    break;
                  }
                }
              }
              input.selectAll("li.patches").data(datum.value).enter()
                .append("li")
                .classed("patches", true)
                
              input.selectAll("li.patches").data(datum.value).exit().remove()
              
              input.selectAll("li.patches")
                .text(function(d) { return JSON.stringify(d)})

              var event = document.createEvent('Event');
              event.initEvent('input', true, true);
              input.node().dispatchEvent(event);
            })
            .each(function(dd, ii) {
              let c = cols[ii];
              let path = "/" + d[key] + "/" + c;
              let match_patch = datum.value.find(function(v) { return v.path == path });
              if (match_patch) {
                d3.select(this).text(String(match_patch.value))
                d3.select(this.parentNode).classed("dirty", true);
              }
            })
        });
    }
    return input
  }
  fieldUI.patch_metadata = patchUI;

  var strUI = function() {
    var datum = this.datum,
        field = this.field,
        target = this.target,
        datasets_in = this.datasets_in,
        module = this.active_module;
  
    var input = target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("input")
          .attr("type", "text")
          .attr("field_id", field.id)
          .attr("value", datum.value)
          .attr("placeholder", datum.default_value)
          .on("change", function(d) { datum.value = this.value });
    return input;
  }
  fieldUI.str = strUI;
  
  var optUI = function() {
    var datum = this.datum,
        field = this.field,
        target = this.target,
        datasets_in = this.datasets_in,
        module = this.active_module;

    var input = target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("select")
          .attr("field_id", field.id)
          .attr("value", (datum.value == null) ? datum.default_value : datum.value)
          .on("change", function(d) { datum.value = this.value })
    input
          .selectAll("option").data(field.typeattr.choices)
            .enter().append("option")
            .attr("value", function(d) {return d[1]})
            .property("selected", function(d) {return d[1] == datum.value})
            .text(function(d) {return d[0]})
    return input;
  }
  fieldUI.opt = optUI;
  
  var floatUI = function() {
    var datum = this.datum,
        field = this.field,
        target = this.target,
        datasets_in = this.datasets_in,
        module = this.active_module;
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
            .attr("placeholder", JSON.stringify(datum.default_value))
            .on("change", function(d) { datum.value = JSON.parse(this.value) });
    } else {
      input = target.append("div")
        .classed("fields", true)
        .datum(datum)
        .append("label")
          .text(field.label)
          .append("input")
            .attr("type", "text")
            .attr("field_id", field.id)
            .attr("value", datum.value)
            .attr("placeholder", JSON.stringify(datum.default_value))
            .on("input", function(d) { datum.value = (this.value == "") ? null : parseFloat(this.value) });
    }
    return input;
  }
  fieldUI.float = floatUI;
  
  var intUI = function() {
    var datum = this.datum,
        field = this.field,
        target = this.target,
        datasets_in = this.datasets_in,
        module = this.active_module;
    var input = target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("input")
          .attr("type", "number")
          .attr("field_id", field.id)
          .attr("value", datum.value)
          .attr("placeholder", JSON.stringify(datum.default_value))
          .on("input", function(d) { datum.value = (this.value == "") ? null : parseInt(this.value) });
    return input;
  }
  fieldUI.int = intUI;
  
  var boolUI = function() {
    var datum = this.datum,
        field = this.field,
        target = this.target,
        datasets_in = this.datasets_in,
        module = this.active_module,
        initial_value = (datum.value == null) ? datum.default_value : datum.value;
    var input = target.append("div")
      .classed("fields", true)
      .datum(datum)
      .append("label")
        .text(field.label)
        .append("input")
          .attr("type", "checkbox")
          .attr("field_id", field.id)
          .property("checked", initial_value)
          .on("change", function(d) { datum.value = this.checked });
    return input;
  }
  fieldUI.bool = boolUI;
  
})(webreduce.editor.make_fieldUI);
