import { Tree, d3 } from '../libraries.js';

/**
 *
 *
 * @export
 * @param {*} plotdata
 * @param {*} plot_controls
 * @param {*} target
 * @param {*} old_plot
 * @returns
 */
export function show_plots_params(plotdata, plot_controls, target, old_plot) {
  plot_controls.updateShow(["export_data"]);
  var params = plotdata.values.map(function (v) { return v.params });
  d3.select(target).selectAll("svg, div").remove();
  d3.select(target).classed("plot", false);
  d3.select(target).append("div")
    .classed("params_controls", true)
    .selectAll(".parambuttons").data(["open all", "close all"])
    .enter()
    .append("button")
    .attr("action", function (d) { return d.replace(" ", "_") })
    .text(function (d) { return d })
    .on("click", function (d) {
      let action = this.getAttribute("action");
      console.log(d3.selectAll('div.paramsDisplay'));
    });

  let param_divs = d3.selectAll([target])
    .selectAll(".paramsDisplay")
    .data(params).enter()
    .append("div")
    .style("overflow", "auto")
    .classed("paramsDisplay", true)

  param_divs.each(function (d, i) {
    let treedata = JSON_to_tree('#', d);
    var tree = new Tree(this, {
      data: [treedata],
      closeDepth: 2,
      itemClickToggle: 'closed'
    });
  });
  return param_divs
}
/**
 *
 *
 * @param {*} name
 * @param {*} value
 * @param {number} [id=0]
 * @returns
 */
function JSON_to_tree(name, value, id = 0) {
  let label = `<label class="json_label">${name}</label>:`;
  if (value == null) {
    return {
      id: id++,
      text: label + `<span class="json_null json_item">null</span>`
    }
  }
  else if (Array.isArray(value)) {
    let return_obj = {
      id: id++,
    }
    if (value.length > 0) {
      let value_el = `<span class="json_array json_item">Array(${value.length})</span>`
      return_obj.text = label + value_el;
      return_obj.children = value.map(function (v, n) { return JSON_to_tree(n, v, id) });
    }
    else {
      return_obj.text = label + `<span class="json_array json_item"> []</span>`;
    }
    return return_obj;
  }
  else if (value instanceof Object) {
    let entries = Object.entries(value);
    let return_obj = {
      id: id++,
    }
    if (entries.length > 0) {
      return_obj.text = label;
      return_obj.children = entries.map(function (nv) { return JSON_to_tree(nv[0], nv[1], id) });
    }
    else {
      return_obj.text = label + `<span class="json_array json_item"> {}</span>`;
    }
    return return_obj;
  }
  else if (typeof (value) == "number") {
    return {
      id: id++,
      text: label + `<span class="json_number json_item">${value}</span>`
    }
  }
  else if (typeof (value) == "string") {
    return {
      id: id++,
      text: label + `<span class="json_string json_item">${value}</span>`
    }
  }
}

function JSON_to_jstree(name, value) {
  let label = `<label>${name}</label>:`;
  if (value == null) {
    return {
      li_attr: { class: "json_null json_item" },
      icon: false,
      text: label + `<span>null</span>`
    }
  }
  else if (Array.isArray(value)) {
    let return_obj = {
      li_attr: { class: "json_array json_item" },
      icon: false
    }
    if (value.length > 0) {
      return_obj.text = label + `Array(${value.length})`;
      return_obj.children = value.map(function (v, n) { return JSON_to_tree(n, v) });
    }
    else {
      return_obj.text = label + " []";
    }
    return return_obj;
  }
  else if (value instanceof Object) {
    let entries = Object.entries(value);
    let return_obj = {
      li_attr: { class: "json_object json_item" },
      icon: false
    }
    if (entries.length > 0) {
      return_obj.text = label;
      return_obj.children = entries.map(function (nv) { return JSON_to_tree(nv[0], nv[1]) });
    }
    else {
      return_obj.text = label + " {}";
    }
    return return_obj;
  }
  else if (typeof (value) == "number") {
    return {
      li_attr: { class: "json_number json_item" },
      icon: false,
      text: label + `<span>${value}</span>`
    }
  }
  else if (typeof (value) == "string") {
    return {
      li_attr: { class: "json_string json_item" },
      icon: false,
      text: label + `<span>${value}</span>`
    }
  }
}