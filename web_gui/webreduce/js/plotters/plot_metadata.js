import { d3 } from '../libraries.js';

export function show_plots_metadata(plotdata, plot_controls, target, old_plot) {
  var metadata = plotdata.values.map(function (v) { return v.values });
  var m0 = metadata[0] || {};

  plot_controls.plotnumber.show = false;
  plot_controls.axes.x.coord.show = false;
  plot_controls.axes.x.transform.show = false;
  plot_controls.axes.y.coord.show = false;
  plot_controls.axes.y.transform.show = false;
  plot_controls.settings.errorbars.show = false;
  plot_controls.settings.points.show = false;
  plot_controls.settings.line.show = false;
  plot_controls.settings.grid.show = false;
  plot_controls.colormap.show = false;

  var colset = new Set(Object.keys(m0));
  for (var nm of metadata.slice(1)) {
    for (var c of colset) {
      if (!(c in nm)) {
        colset.delete(c);
      }
    }
  }
  var cols = Array.from(colset);
  d3.select(target).selectAll("svg, div").remove();
  d3.select(target).classed("plot", false);
  let metadata_table = d3.select(target).append("div").append("table").classed("metadata", true)
  metadata_table
    .append("thead").append("tr")
    .selectAll(".colHeader")
    .data(cols).enter()
    .append("th")
    .classed("colHeader", true)
    .text(function (d) { return String(d) })

  metadata_table
    .append("tbody")
    .selectAll(".metadata-row")
    .data(metadata).enter()
    .append("tr")
    .classed("metadata-row", true)
    .on("click", function () {
      metadata_table.selectAll(".metadata-row")
        .classed("active", false);
      d3.select(this).classed("active", true);
    })
    .each(function (d) {
      let row = d3.select(this);
      cols.forEach(function (c) {
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
