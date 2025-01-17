
import { d3, extend, xyChart } from '../libraries.js';
import { app } from '../main.js'

function merge_1d_plotdata(plotdata) {
  const values = plotdata.values;
  let datas = [];
  let series = [];
  let xlabel, ylabel;
  values.forEach(function (v) {
    series = series.concat(v.options.series || [{}]);
    datas = datas.concat(v.data);
    if (v.options && v.options.axes) {
      if (v.options.axes.xaxis && v.options.axes.xaxis.label != null) {
        const new_xlabel = v.options.axes.xaxis.label;
        if (xlabel != null && xlabel != new_xlabel) {
          alert("inconsistent x-axis: " + xlabel + ", " + new_xlabel);
        }
        xlabel = new_xlabel;
      }
      if (v.options.axes.yaxis && v.options.axes.yaxis.label != null) {
        const new_ylabel = v.options.axes.yaxis.label;
        if (ylabel != null && ylabel != new_ylabel) {
          alert("inconsistent y-axis: " + ylabel + ", " + new_ylabel);
        }
        ylabel = new_ylabel;
      }
    }
  })
  const output = {
    options: {
      series: series,
      axes: {
        xaxis: { label: xlabel },
        yaxis: { label: ylabel }
      }
    },
    data: datas,
    type: "1d"
  }
  return output;
}

export async function show_plots_1d(plotdata, plot_controls, target, old_plot) {
  const merged = merge_1d_plotdata(plotdata);
  const options = {
    series: [],
    legend: { show: true, left: 150 },
    axes: { xaxis: { label: "x-axis" }, yaxis: { label: "y-axis" } }
  };
  extend(true, options, merged.options);
  if (options.xtransform) {
    plot_controls.axes.x.transform.value = options.xtransform;
  } else {
    options.xtransform = plot_controls.axes.x.transform.value;
  }
  if (options.ytransform) {
    plot_controls.axes.y.transform.value = options.ytransform;
  } else {
    options.ytransform = plot_controls.axes.y.transform.value;
  }

  options.show_errorbars = plot_controls.settings.errorbars.value;
  options.show_points = plot_controls.settings.points.value;
  options.show_line = plot_controls.settings.line.value;


  // create the 1d chart:
  const mychart = new xyChart(options, d3);
  d3.select(target).selectAll("svg, div").remove();
  d3.select(target).classed("plot", true);
  d3.selectAll([target])
    .data([merged.data])
    .call(mychart);
  mychart.zoomRect(true);
  app.callbacks.resize_center = mychart.autofit;

  plot_controls.updateShow([
    "axes/x/transform",
    "axes/y/transform",
    "settings/errorbars",
    "settings/points",
    "settings/line",
    "download_svg",
    "export_data"
  ]);

  plot_controls.settingChange = function (setting_name, value) {
    const o = mychart.options();
    let opt_name = 'show_' + setting_name;
    o[opt_name] = value;
    mychart.options(o).update();
  }
  plot_controls.transformChange = function (axis, transform) {
    mychart[axis + 'transform'](transform);
  }

  return mychart
}