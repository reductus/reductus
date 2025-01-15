import {server_api} from './server_api/api_msgpack.js';
import { extend, dataflowEditor, d3 } from './libraries.js';

var debug = false;

window.onload = async function() {
  await server_api.__init__();

  let e = new dataflowEditor(null, d3); //Class2.editorFactory();
  e._outer = []; // contexts for embedded templates;
  e._clipboard = null;
  d3.select("#editor_div").call(e);

  // brush stuff //
  var brush = d3.brush().on("end", brushended),
    idleTimeout,
    idleDelay = 350;

  e.svg().append("g")
      .attr("class", "brush")
      
  function idled() {
    idleTimeout = null;
  }
    
  function brushed(d,i) {
    console.log('brushed', d, i, this);
  }
  function brushended(d, i) {
    var s = d3.event.selection;
    if (!s) {
      if (!idleTimeout) return idleTimeout = setTimeout(idled, idleDelay);
    } else {
      var checker = insideChecker(s);
      //console.log(s, e.svg().selectAll("g.module").filter(checker));
      e.svg().selectAll("g.module").filter(checker).classed("highlight", true);
      e.svg().select("g.brush").call(brush.move, null);
    }
  }

  function insideChecker(s) {
    var xmin = s[0][0],
        ymin = s[0][1],
        xmax = s[1][0],
        ymax = s[1][1];
        
    var isInside = function(d,i) {
      var ds = d3.select(this).select("rect.title");
      var width = +ds.attr("width")
      var height = +ds.attr("height")

      var i = (
        d.x >= xmin && 
        d.x + width <= xmax &&
        d.y >= ymin &&
        d.y + height <= ymax
      )
      return i
    }
    return isInside
  }
        

  function add_brush() {
    e.svg().select("g.brush")
      .call(brush)
  }
  // end brush stuff //

  e.add_brush = add_brush;

  var contextMenuShowing = false;

  e.dispatch.on("drag_module", function(module_data, dx, dy) {
    var module = d3.select(this);
    if (module.classed("highlight")) {
      var other_modules = e.svg().selectAll("g.module.highlight")
        .filter(function(d) { return d.module_id != module_data.module_id });
        
      other_modules
        .each(function(d) { d.x += dx; d.y += dy })
        .attr("transform", function(d) { 
          return "translate(" + d.x.toFixed() + "," + d.y.toFixed() + ")"
        })
    }
  })

  e.container.on('click.multiselect', function(d,i) {
    var d3_target = d3.select(d3.event.target);
    if (contextMenuShowing) {
        d3.event.preventDefault();
        d3.select(".popup").remove();
        contextMenuShowing = false;
    }
    if (d3_target.classed("title") && (d3.event.shiftKey || d3.event.ctrlKey)) {
      d3.event.preventDefault();
      d3.event.stopPropagation();
      var module = d3.select(d3.event.target.parentNode.parentNode);
      module.classed("highlight", !module.classed("highlight"))
      return
    }
    else {
      e.container.selectAll("g.module").classed("highlight", false);
    }
  })

  e.container.on('contextmenu',function (d,i) {
    if (contextMenuShowing) {
      d3.event.preventDefault();
      d3.select(".popup").remove();
      contextMenuShowing = false;
    } 
    else {
      var d3_target = d3.select(d3.event.target);
      var target_pos = [d3.event.x, d3.event.y];
      var grandparent = d3.select(d3.event.target.parentNode.parentNode);
      // case: wire selected
      if (d3_target.classed("wire")) {
          d3.event.preventDefault();
          contextMenuShowing = true;

          // Build the popup            
          var popup = d3.select("body")
            .append("div")
            .attr("class", "popup")
            .style("left", d3.event.x + "px")
            .style("top", d3.event.y + "px")
          
          var ul = popup.append("ul")
          
          ul.append("li").text("delete").on("click", function() {
              var active_data = d3_target.datum();
              var parentNode = d3_target.node().parentNode;
              var wires = d3.select(parentNode).datum().wires;
              for (var i=0; i<wires.length; i++) {
                  var w = wires[i]; 
                  if (w.source == active_data.source && w.target == active_data.target) {
                      wires.splice(i,1);
                      break;
                  }
              };
              e.update();
              popup.remove(); 
              contextMenuShowing=false;
              
          });
      }
      else if (d3_target.classed("exposed-wire")) {
        // case: wire to exposed terminal selected
        d3.event.preventDefault();
        contextMenuShowing = true;

        // Build the popup            
        var popup = d3.select("body")
          .append("div")
          .attr("class", "popup")
          .style("left", d3.event.x + "px")
          .style("top", d3.event.y + "px")
        
        var ul = popup.append("ul")
        
        ul.append("li").text("delete").on("click", function() {
          var active_data = d3_target.datum();
          if (active_data.source[0] == -1) {
            e.svg().datum().inputs.forEach(function(f) { 
              if (f.id == active_data.source[1]) {
                f.target = null;
              }
            });
          }
          if (active_data.target[0] == -1) {
            e.svg().datum().outputs.forEach(function(f) { 
              if (f.id == active_data.target[1]) {
                f.target = null;
              }
            });
          }
          e.update();
          popup.remove(); 
          contextMenuShowing=false;
        });
      }
      else if (d3_target.classed("title")) {
        // case: module title selected
        d3.event.preventDefault();
        if (grandparent.classed("highlight")) {
          // bulk operation on modules
          contextMenuShowing = true;

          // Build the popup            
          var popup = d3.select("body")
            .append("div")
            .attr("class", "popup")
            .style("left", d3.event.x + "px")
            .style("top", d3.event.y + "px")
          
          var ul = popup.append("ul");
          
          var copy = function() {
            popup.remove();
            var datum = e.svg().datum();
            var modules_to_copy = []; 
            var module_index_lookup = {};
            e.svg().selectAll("g.module.highlight").each(function(d,i) {
              modules_to_copy.push(d);
              var old_index = this.getAttribute("index");
              module_index_lookup[old_index] = i;
            });
            modules_to_copy = extend(true, [], modules_to_copy);
            var wires_to_copy = [];
            datum.wires.forEach(function(w,i) { 
              var ks = w.source[0].toString(),
                  kt = w.target[0].toString();
              if (ks in module_index_lookup && kt in module_index_lookup) {
                var new_wire = extend(true, {}, w);
                new_wire.source[0] = module_index_lookup[ks];
                new_wire.target[0] = module_index_lookup[kt];
                wires_to_copy.push(new_wire);
              }
            });
            modules_to_copy.forEach(function(d) { delete d.module_id });
            var content = {"modules": modules_to_copy, "wires": wires_to_copy}
            e._clipboard = {reference_pos: target_pos, content: content};
            e.update();
            contextMenuShowing=false;
          }
          
          var cut = function() {
            copy();
            var to_cut = [];
            e.svg().selectAll("g.module.highlight").each(function(d,i) {
              to_cut.push(d.module_id);
            });
            e._clipboard.to_cut = to_cut;
          }
          
          var buttons = ul.append("li").style("text-align", "right")
          buttons
            .append("button").text("cut").on("click", cut);
          buttons
            .append("button").text("copy").on("click", copy);
          buttons
            .append("button").text("delete modules")
              .on("click", function() {
                var modules = e.svg().datum().modules || [];
                e.svg().selectAll("g.module.highlight").each(function(d) { 
                  modules = modules.filter(function(m) { return m.module_id != d.module_id });
                })
                e.svg().datum().modules = modules;
                popup.remove(); 
                e.update();
                contextMenuShowing=false;
              });
        } 
        else {
          // operation on single module
          contextMenuShowing = true;

          // Build the popup
          var module = grandparent.datum();
          var fields = [];
          if (module && module_defs[module.module] && module_defs[module.module].fields) {
              fields = module_defs[module.module].fields;
          } 
          
          var popup = d3.select("body")
            .append("div")
            .attr("class", "popup")
            .style("left", d3.event.x + "px")
            .style("top", d3.event.y + "px")
          
          var ul = popup.append("ul")
          
          ul.append("li").text("Edit title")
            .on("click", function() {
              popup.remove();
              contextMenuShowing=false;
              var new_title = prompt("New title:", module.title);
              if (new_title != null) {
                module.title = new_title;
                e.import(e.export());
              }                  
            });
          if (fields.length > 0) {
            ul.append("ul").text("Configure:").selectAll('li').data(fields)
                .enter()
                .append("li")
                    .text(function(d) {return d.id})
                    .on("click", function(d,i) {
                      popup.remove();
                      contextMenuShowing = false;
                      edit_field(module, d, i);
                    })
          }
          ul.append("hr")
          ul.append("li").text("delete").on("click", function() {
              var module_id = d3_target.datum().module_id;
              e.svg().datum().modules = e.svg().datum().modules.filter(function(d) { return d.module_id != module_id});
              popup.remove(); 
              e.update();
              contextMenuShowing=false;
          });
        }
      }
      else if ((d3_target.classed("input") || d3_target.classed("output")) && d3_target.classed("exposed")) {
          d3.event.preventDefault();
          contextMenuShowing = true;
          
          // Build the popup            
          popup = d3.select("body")
            .append("div")
            .attr("class", "popup")
            .style("left", d3.event.x + "px")
            .style("top", d3.event.y + "px")
            
          var ul = popup.append("ul");
          
          var side = d3_target.classed("output") ? "inputs" : "outputs";
          ul.append("li").text("delete").on("click", function() {
              var term_id = grandparent.datum().id;
              e.svg().datum()[side] = e.svg().datum()[side].filter(function(d) { 
                return d.id != term_id
              });
              popup.remove(); 
              e.update();
              contextMenuShowing=false;
          });

      }
      else if (e._clipboard != null) {
        d3.event.preventDefault();
        contextMenuShowing = true;
        
        var to_paste = extend(true, {}, e._clipboard.content);
        var rx = e._clipboard.reference_pos[0];
        var ry = e._clipboard.reference_pos[1];
        // Build the popup            
        popup = d3.select("body")
          .append("div")
          .attr("class", "popup")
          .style("left", d3.event.x + "px")
          .style("top", d3.event.y + "px")
        
        var ul = popup.append("ul")
        
        ul.append("li").text("paste").on("click", function() {
            popup.remove();
            var datum = e.svg().datum();
            if (e._clipboard.to_cut) {
              var modules = datum.modules || [];
              modules = modules.filter(function(m) { return (e._clipboard.to_cut.indexOf(m.module_id) < 0) });
              datum.modules = modules;
              e.update();
              e._clipboard.to_cut = null;
            }
            
            var start_module_index = (datum.modules || []).length;
            
            to_paste.modules.forEach(function(m) {
              m.x += d3.event.x - rx;
              m.y += d3.event.y - ry;
            });
            to_paste.wires.forEach(function(w) {
              w.source[0] += start_module_index;
              w.target[0] += start_module_index;
            })
            
            e.svg().selectAll("g.module.highlight").classed("highlight", false);              
            datum.modules.push.apply(datum.modules, to_paste.modules);
            e.update();
            datum.wires.push.apply(datum.wires, to_paste.wires)
            e.update();
            e.svg().selectAll("g.module").filter(function(d,i) { return i >= start_module_index }).classed("highlight", true);
            contextMenuShowing=false;
        });
      }
      else {
        // should only get here if the target is the editor itself, with an empty clipboard:
        // show menu to add a new module.
        d3.event.preventDefault();
        contextMenuShowing = true;
        
        let window_x = d3.event.x;
        let window_y = d3.event.y;
        let [x,y] = d3.mouse(e.svg().node());
        // Build the popup            
        popup = d3.select("body")
          .append("div")
          .attr("class", "popup")
          .style("left", window_x + "px")
          .style("top", window_y + "px")
        
        popup.append("div").text("Add new module:");
        
        let module_select = popup.append("select");
        let module_defs = e.module_defs();
        // list of name, id pairs:
        let module_options = ([["Add new module:", ""]]).concat(
          Object.values(module_defs)
            .filter((module) => (module.visible))
            .map((module) => [module.name, module.id])
        );
        module_select.selectAll("option").data(module_options)
          .enter().append('option')
          .attr("value", function(d) {return d[1]}) // function(d) {return module_defs[d].module})
          .attr("title", function(d) {return d[0]})
          .text(function(d) {return d[0]})  
        
        module_select.on("change", function() {
          popup.remove();
          contextMenuShowing=false;
          let module = this.value;
          let title = module_defs[module].name;
          e.svg().datum().modules.push({module, title, x, y});
          e.update();
        });
      }
    }
  })

  function edit_field(module, d, i) {
    var field_id = d.id,
        field_default = d.default;
    var config = (module.config || {})[field_id];
    if (config == null) {
      config = field_default;
    }        
    var popup = d3.select("body")
              .append("div")
              .attr("class", "popup")
              .style("left", "20px")
              .style("top", "30px")
    
    popup.append("div")
      .text("Editing: " + d.id);
    var input = popup.append("div")
      .append("textarea")
      .attr("rows", "10")
      .style("width", "95%")
      .property("value", JSON.stringify(config))
      //.text(JSON.stringify(config))
    
    var feb = popup.append("div")
    
    feb.append("button")
      .attr("value", "submit")
      .text("submit")
      .on("click", function() {
        
        var value = input.property("value");
        try {
          var parsed_val = JSON.parse(value);
          if (!module.config) {module.config = {}};
          module.config[field_id] = parsed_val;
          popup.remove();
        }
        catch (error) {
          alert("invalid JSON value: " + value);
        }
      });
    feb.append("button")
      .attr("value", "cancel")
      .text("cancel")
      .on("click", function() {
        popup.remove();
      });
  }

  let instruments = {};
  let module_defs = {};
  var module_names;

  function load_instrument(instrument_id, update_selector) {
    if (debug) { console.log('#select_instrument option[value="' + instrument_id + '"]', d3.select('#select_instrument option[value="' + instrument_id + '"]'));}
    if (update_selector) {
      d3.select('#select_instrument option[value="' + instrument_id + '"]').property("selected", true);
    }
    var current_instrument = instrument_id; 
    return server_api.get_instrument({instrument_id: current_instrument})
      .then(function(instrument_def) {
        instruments[current_instrument] = instrument_def;
        module_defs = {};
        if ('modules' in instrument_def) {
          for (var i=0; i<instrument_def.modules.length; i++) {
            var m = instrument_def.modules[i];
            module_defs[m.id] = m;
          }
        }
        // pass it through:
        e.module_defs(module_defs);
        return instrument_def;
      })
      .then(function() {
        module_names = (["Add new module:"])
          .concat(
            Object.keys(module_defs).filter(function(mname) {
              let module = module_defs[mname];
              return (module.visible != false)
            })
          );
        d3.selectAll("#new_module option").remove()
        d3.select("#new_module").append("option").text("Add new module:");
        d3.select("#new_module").selectAll("option").data(module_names)
          .enter().append('option')
          .attr("module", function(d) {return d}) // function(d) {return module_defs[d].module})
          .text(function(d) {return module_defs[d].name})  
      });
  }
    
  d3.select('#new_module').on("change", function(ev) {
      var title = this.value,
          module = module_names[this.selectedIndex];
      e.svg().datum().modules.push({module: module, title: title});
      e.update();
      this.selectedIndex=0;
  });


  d3.select("#show_value").on("click", function() { 
    var win = window.open();
    win.document.write("<pre>" + JSON.stringify(e.export(), null, 2) + "</pre>");
  });

  function loadDataFromFile() {
      var file = document.getElementById('upload_template').files[0]; // only one file allowed
      datafilename = file.name;
      var result = null;
      var reader = new FileReader();
      reader.onload = function(ev) {
          var template = JSON.parse(this.result);
          e.import(template);
      }
      reader.readAsText(file);
  }

  // expose these critical pieces, that the main application needs to use on load
  window.load_instrument = load_instrument;
  window.e = e;

  server_api.list_instruments()
    .then(function(instruments) {
      d3.select("#select_instrument").selectAll("option").data(instruments)
        .enter().append("option")
          .attr("value", function(d) { return d })
          .text(function(d) { return d });
      return instruments;
    })
    //.then(function() {load_instrument(window.current_instrument, true)});
    .then(function() {
      var event = new Event('editor_ready');
      window.dispatchEvent(event);
    })

}