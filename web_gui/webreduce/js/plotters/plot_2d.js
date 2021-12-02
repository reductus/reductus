import { d3, get_colormap, colormap_names, heatChartMultiMasked, heatChart } from '../libraries.js';
import { app } from '../main.js';

export async function show_plots_2d_multi(plotdata, plot_controls, target, old_plot) {
  var aspect_ratio = null,
    values = plotdata.values,
    mychart = old_plot;
  var data;
  let options = { margin: { left: 100 } };

  if (mychart == null || mychart.type != "heatmap_2d_multi") {
    d3.select(target).selectAll("svg, div").remove();
    d3.select(target).classed("plot", true);

    mychart = new heatChartMultiMasked(options, d3);
    data = values[0];
    await plot_controls.$nextTick();
    d3.selectAll([target]).data([values[0].datasets]).call(mychart);
    app.callbacks.resize_center = function () { mychart.autofit() };
  }
    
  if (options.ztransform) {
    plot_controls.axes.z.transform.value = options.ztransform;
  } else {
    options.ztransform = plot_controls.axes.z.transform.value;
  }

  plot_controls.updateShow([
    "plotnumber",
    "axes/z",
    "settings/grid",
    "colormap",
    "export_data"
  ])

  plot_controls.colormap.options = colormap_names;

  plot_controls.settingChange = function (setting_name, value) {
    var o = mychart.options();
    let opt_name = 'show_' + setting_name;
    o[opt_name] = value;
    mychart.options(o).update();
  }

  plot_controls.transformChange = function (axis, transform) {
    mychart[axis + 'transform'](transform);
  }
  plot_controls.colormapChange = function (colormap_name) {
    var new_colormap = get_colormap(colormap_name, d3);
    mychart.colormap(new_colormap).redrawImage();
    mychart.colorbar.update();
  }
  plot_controls.plotNumberChange = function (plotnum) {
    var plotnum = plotnum || 0;
    let data = values[plotnum];
    plot_controls.$emit("plot-title", data.title || "");
    data.ztransform = plot_controls.axes.z.transform.value;
    var aspect_ratio = null;
    if ((((data.options || {}).fixedAspect || {}).fixAspect || null) == true) {
      aspect_ratio = ((data.options || {}).fixedAspect || {}).aspectRatio || null;
    }
    mychart.options(data.options);
    mychart
      .aspect_ratio(aspect_ratio)
      .xlabel(data.xlabel)
      .ylabel(data.ylabel);
    var new_colormap = get_colormap(plot_controls.colormap.value, d3);
    mychart.colormap(new_colormap);
    mychart.source_data(data.datasets);
    mychart.zoomScroll(true);
    mychart.ztransform(plot_controls.axes.z.transform.value);
  }

  plot_controls.plotnumber.max = plotdata.values.length - 1;
  mychart.interactors(null);
  plot_controls.plotNumberChange(0);
  mychart.autofit();
  return mychart
}

export function show_plots_2d(plotdata, plot_controls, target, old_plot) {
  var aspect_ratio = null,
    values = plotdata.values,
    mychart = old_plot;
  var data;
  let options = { margin: { left: 100 } };

  // set up plot control buttons and options:
  if (mychart == null || mychart.type != "heatmap_2d") {
    d3.select(target).selectAll("svg, div").remove();
    d3.select(target).classed("plot", true);

    mychart = new heatChart(options, d3);
    data = values[0];
    d3.selectAll([target]).data([values[0].z]).call(mychart);
    app.callbacks.resize_center = function () { mychart.autofit() };
  }

  if (options.ztransform) {
    plot_controls.axes.z.transform.value = options.ztransform;
  } else {
    options.ztransform = plot_controls.axes.z.transform.value;
  }

  plot_controls.updateShow([
    "plotnumber",
    "axes/z",
    "settings/grid",
    "colormap"
  ])

  plot_controls.colormap.options = colormap_names;

  plot_controls.settingChange = function (setting_name, value) {
    var o = mychart.options();
    let opt_name = 'show_' + setting_name;
    o[opt_name] = value;
    mychart.options(o).update();
  }

  plot_controls.transformChange = function (axis, transform) {
    mychart[axis + 'transform'](transform);
  }
  plot_controls.colormapChange = function (colormap_name) {
    var new_colormap = get_colormap(colormap_name, d3);
    mychart.colormap(new_colormap).redrawImage();
    mychart.colorbar.update();
  }
  plot_controls.plotNumberChange = function (plotnum) {
    var plotnum = plotnum || 0;
    data = values[plotnum];
    plot_controls.$emit("plot-title", data.title || "");
    data.ztransform = plot_controls.axes.z.transform.value;
    var aspect_ratio = null;
    if ((((data.options || {}).fixedAspect || {}).fixAspect || null) == true) {
      aspect_ratio = ((data.options || {}).fixedAspect || {}).aspectRatio || null;
    }
    mychart
      .autoscale(true)
      .aspect_ratio(aspect_ratio)
      .dims(data.dims)
      .xlabel(data.xlabel)
      .ylabel(data.ylabel);
    var new_colormap = get_colormap(plot_controls.colormap.value, d3);
    mychart.colormap(new_colormap);
    mychart.source_data(data.z[0]);
    mychart.zoomScroll(true);
    mychart.ztransform(plot_controls.axes.z.transform.value);
  }

  plot_controls.plotnumber.max = plotdata.values.length - 1;
  mychart.interactors(null);
  plot_controls.plotNumberChange(0);
  mychart.autofit();
  return mychart
}