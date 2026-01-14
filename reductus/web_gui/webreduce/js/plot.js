import * as Vue from 'vue';
import { PlotControls } from './plotters/plot_controls.js';
import { app } from './main.js';
import { show_plots_nd } from './plotters/plot_nd.js';
import { show_plots_2d_multi, show_plots_2d } from './plotters/plot_2d.js';
import { show_plots_metadata } from './plotters/plot_metadata.js';
import { show_plots_params } from './plotters/plot_params.js';
import { show_plots_1d } from './plotters/plot_1d.js';

const plotter = {};
export { plotter };

let template = `
<div class="reductus-plot-panel">
  <header id="plot_title">{{title}}</header>
  <div id="plotdiv" class="plotdiv" ref="plotdiv">
  </div>
  <plot-controls
    ref="controls"
    style="min-height:2em;"
    @plot-title="set_plot_title"
    @transformChange="transformChange"
    @settingChange="settingChange"
    @downloadSVG="downloadSVG"
    @export-data="emitter.emit('plotter.action', 'export_data')"
  ></plot-controls>
</div>
`;

const plotters = {
  '1d': show_plots_1d,
  'nd': show_plots_nd,
  '2d_multi': show_plots_2d_multi,
  '2d': show_plots_2d,
  'metadata': show_plots_metadata,
  'params': show_plots_params,
  'null': (data, controls, plotdiv) => { 
    controls.updateShow([]); 
    plotdiv.innerHTML="<div><h1 style=\"text-align:center;\">&#8709</h1></div>";
  }
};

export const PlotPanel = {
  name: 'plot-panel',
  components: { PlotControls },
  props: {
    emitter: Object
  },
  data: () => ({
    type: 'null',
    instances: {},
    active_plot: null,
    plot_controls: null,
    title: ""
  }),
  mounted() {
    // Listen for show_plots events
    this.emitter.on('show_plots', this.showPlots);
  },
  beforeUnmount() {
    // Clean up listener
    this.emitter.off('show_plots', this.showPlots);
  },
  methods: {
    async showPlots(results) {
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
      if (new_plotdata == null) {
        await this.setPlotData({type: 'null'});
      }
      else if (['nd', '1d', '2d', '2d_multi', 'params', 'metadata'].includes(new_plotdata.type)) {
        await this.setPlotData(new_plotdata);
      }
    },
    transformChange(axis, new_transform) {
      console.log(`changing transform for axis ${axis} to ${new_transform}`);
    },
    settingChange(name, value){
      console.log(`setting change: ${name} to ${value}`);
    },
    downloadSVG() {
      let svg = this.active_plot.export_svg();
      let serializer = new XMLSerializer();
        var output = serializer.serializeToString(svg);
        var filename = prompt("Save svg as:", "plot.svg");
        if (filename == null) { return } // cancelled
        app.download(output, filename);
    },
    set_plot_title(title) {
      this.title = title;
    },
    async setPlotData(plotdata) {
      let typeChange = (this.type != plotdata.type);
      console.log(`plot type change: ${this.type} -> ${plotdata.type}`);
      this.type = plotdata.type;
      this.title = "";
      await this.$nextTick();
      if (!this.$refs.controls || !this.$refs.plotdiv) {
        console.warn('Plot refs not ready yet');
        return;
      }
      const plotter_fn = plotters[plotdata.type];
      if (!plotter_fn) {
        console.warn(`Unknown plot type: ${plotdata.type}`);
        return;
      }
      this.active_plot = await plotter_fn(plotdata, this.$refs.controls, this.$refs.plotdiv, this.active_plot);
    },
    // setPlotData(plotdata) {
    //   if (!plotdata || plotdata.type === 'null') {
    //     this.type = 'null';
    //     this.instances = {};
    //     this.active_plot = null;
    //   } else {
    //     this.type = plotdata.type || 'null';
    //     const plotter_fn = plotters[this.type] || plotters['null'];
    //     const plotdiv = this.$refs.plotdiv;
    //     const controls = this.$refs.controls;
    //     if (plotdiv && controls) {
    //       plotter_fn(plotdata, controls, plotdiv);
    //       this.active_plot = plotdata;
    //     }
    //   }
    // }
  },
  template  
};


plotter.plot = function(plotdata) {
  this.instance.setPlotData(plotdata);
}

class Deferred {
  constructor() {
      this.promise = new Promise((resolve, reject) => {
          this.resolve = resolve;
          this.reject  = reject;
      });
  }
}

plotter.create_instance = function(target_id, emitter) {
  let target = document.getElementById(target_id);
  plotter.instance = Vue.createApp(PlotPanel, {
    emitter: emitter,
  }).mount(target);
}




