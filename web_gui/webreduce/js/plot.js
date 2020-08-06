import { Vue } from './libraries.js';
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
<div class="plot-panel"
  style="flex:1;display:flex;flex-direction:column;">
  <div id="plotdiv" class="plotdiv" ref="plotdiv" style="flex:1;">
  </div>
  <plot-controls
    ref="controls"
    style="min-height:2em;"
    @transformChange="transformChange"
    @settingChange="settingChange"
    @downloadSVG="downloadSVG"
    @mounted = "controlsMounted"
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
  data: () => ({
    type: 'null',
    instances: {},
    active_plot: null
  }),
  methods: {
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
    }
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

plotter.create_instance = function(target_id) {
  let target = document.getElementById(target_id);
  let plotPanelMounted = new Deferred();
  let plotControlsMounted = new Deferred();
  const PlotPanelClass = Vue.extend(PlotPanel);
  plotter.instance = new PlotPanelClass({
    data: () => ({
      type: 'null',
      instances: {},
      active_plot: null,
      plot_controls: null
    }),
    methods: {
      async setPlotData(plotdata) {
        let typeChange = (this.type != plotdata.type);
        this.type = plotdata.type;
        await this.$nextTick();
        await this.ready();
        if (!this.$refs.control) {return}
        this.active_plot = await plotters[plotdata.type](plotdata, this.$refs.controls, this.$refs.plotdiv, this.active_plot);
      },
      async ready() {
        return Promise.all([
          plotPanelMounted.promise,
          //plotControlsMounted.promise
        ]);
      },
      controlsMounted() {
        console.log("controls mounted");
        plotControlsMounted.resolve(true);
      }
    },
    mounted: function() {
      plotPanelMounted.resolve(true);
    }
  }).$mount(target);

}

