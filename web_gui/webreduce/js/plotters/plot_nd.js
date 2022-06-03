import { d3, extend, xyChart } from '../libraries.js';
import { app } from '../main.js'

export async function show_plots_nd(plotdata, plot_controls, target, old_plot) {
  plotdata = merge_nd_plotdata(plotdata);
  var options = {
    series: [],
    legend: { show: true, left: 150 },
    axes: { xaxis: { label: "x-axis" }, yaxis: { label: "y-axis" } }
  };
  extend(true, options, plotdata.options);

  var colnames = Object.keys(plotdata.columns).sort();
  plot_controls.$set(plot_controls.axes.x.coord, 'options', colnames);
  plot_controls.$set(plot_controls.axes.y.coord, 'options', colnames);
  plot_controls.$set(plot_controls.axes.x.transform, 'options', ["linear", "log", "ln", "pow(2)", "pow(4)"]);
  plot_controls.$set(plot_controls.axes.y.transform, 'options', ["linear", "log", "ln", "pow(2)", "pow(4)"]);

  if (options.xcol) {
    plot_controls.axes.x.coord.value = options.xcol;
  } else {
    options.xcol = plot_controls.axes.x.coord.value
  }
  if (options.ycol) {
    plot_controls.axes.y.coord.value = options.ycol;
  } else {
    options.ycol = plot_controls.axes.y.coord.value
  }

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

  var xcol = options.xcol || "x";
  var ycol = options.ycol || "y";

  var chartdata = make_chartdata(plotdata.data, xcol, ycol);
  // create the nd chart:
  var mychart = new xyChart(options, d3);

  plot_controls.updateShow([
    "axes/x", 
    "axes/y", 
    "settings/errorbars", 
    "settings/points", 
    "settings/line",
    "download_svg",
    "export_data"
  ]);

  plot_controls.settingChange = function(setting_name, value) { 
    var o = mychart.options();
    let opt_name = 'show_' + setting_name;
    o[opt_name] = value;
    mychart.options(o).update();
  }

  plot_controls.coordChange = function(axis, coord) {
    xcol = (axis == 'x') ? coord : xcol;
    ycol = (axis == 'y') ? coord : ycol;
    var new_data = make_chartdata(plotdata.data, xcol, ycol);
    var xlabel = plotdata.columns[xcol].label + " (" + plotdata.columns[xcol].units + ")";
    var ylabel = plotdata.columns[ycol].label + " (" + plotdata.columns[ycol].units + ")";
    var o = mychart.options();
    o.axes.xaxis.label = xlabel;
    o.axes.yaxis.label = ylabel;
    mychart.options(o).source_data(new_data).resetzoom();
  }

  plot_controls.transformChange = function(axis, transform) {
    mychart[axis + 'transform'](transform);
  }

  var tooltip = d3.select("body").append("div").classed("tooltip", true);
  var tip_prec = 4;
  d3.select(target).selectAll(".dot")
    .on("mouseover", function (d) {
      tooltip.transition()
        .duration(200)
        .style("opacity", .9);
      tooltip.html("x: " + d[0].toPrecision(tip_prec) + "<br/>y: " + d[1].toPrecision(tip_prec))
        .style("left", (d3.event.pageX + 10) + "px")
        .style("top", (d3.event.pageY - 35) + "px");
    })
    .on("mouseout", function (d) {
      tooltip.transition()
        .duration(500)
        .style("opacity", 0);
    });

    await plot_controls.$nextTick();
    d3.select(target).selectAll("svg, div").remove();
    d3.select(target).classed("plot", true);
    d3.selectAll([target])
      .data([chartdata])
      .call(mychart);
    mychart.zoomRect(true);
    app.callbacks.resize_center = mychart.autofit;

  return mychart
};

function make_chartdata(data, xcol, ycol) {
  var chartdata = data.map(function (colset) {
    var x = colset[xcol].values,
      y = colset[ycol].values,
      dx = colset[xcol].errorbars,
      dy = colset[ycol].errorbars,
      dataset = [];
    if (dx != null || dy != null) {
      for (var i = 0; i < x.length && i < y.length; i++) {
        var errorbar = {};
        if (dx && dx[i] != null) { errorbar.xlower = x[i] - dx[i]; errorbar.xupper = x[i] + dx[i] }
        else { errorbar.xlower = errorbar.xupper = x[i]; }

        if (dy && dy[i] != null) { errorbar.ylower = y[i] - dy[i]; errorbar.yupper = y[i] + dy[i] }
        else { errorbar.ylower = errorbar.yupper = y[i]; }

        dataset[i] = [x[i], y[i], errorbar];
      }
    }
    else {
      dataset = zip_arrays(x, y);
    }
    return dataset;
  });
  return chartdata;
};

function zip_arrays() {
  var args = [].slice.call(arguments);
  var shortest = args.length == 0 ? [] : args.reduce(function (a, b) {
    return a.length < b.length ? a : b
  });

  return shortest.map(function (_, i) {
    return args.map(function (array) { return array[i] })
  });
};

function merge_nd_plotdata(plotdata) {
  var values = plotdata.values;
  var column_sets = values.map(function (pd) {
    return pd.columns
  });
  var all_columns = column_sets[0];
  column_sets.forEach(function (new_cols) {
    // match by label.
    var ncl = Object.keys(new_cols).map(function (nc) { return new_cols[nc].label })
    for (var c in all_columns) {
      var cl = all_columns[c].label;
      if (ncl.indexOf(cl) < 0) {
        delete all_columns[c];
      }
    }
  });
  var datas = [];
  var series = [];
  var xcol;
  var ycol;
  var xtransform;
  var ytransform;

  values.forEach(function (pd) {
    var colset = {}
    for (var col in all_columns) {
      if (all_columns.hasOwnProperty(col)) {
        colset[col] = pd.datas[col];
      }
    }
    datas.push(colset);
    series.push({ label: pd.title });
    xcol = xcol || pd.options.xcol;
    ycol = ycol || pd.options.ycol;
    xtransform = xtransform || pd.options.xtransform;
    ytransform = ytransform || pd.options.ytransform;
  });

  if (!(ycol in all_columns)) {
    ycol = Object.keys(all_columns)[1];
  }

  var plottable = {
    type: "nd",
    columns: all_columns,

    options: {
      series: series,
      axes: {
        xaxis: { label: all_columns[xcol].label + "(" + all_columns[xcol].units + ")" },
        yaxis: { label: all_columns[ycol].label + "(" + all_columns[ycol].units + ")" }
      },
      xcol: xcol,
      ycol: ycol,
      errorbar_width: 0
    },
    data: datas
  }

  if (xtransform != null) {
    plottable.options.xtransform = xtransform;
  }
  if (ytransform != null) {
    plottable.options.ytransform = ytransform;
  }

  return plottable

};