import { d3, extend, scaleInteractor } from '../../libraries.js';
import { plotter } from '../../plot.js';

let template = `
<div class="fields">
  <label>
    {{field.label}}
    <textarea
      :id="field.id"
      :placeholder="field.default"
      :rows="dimensioned_value.length+2"
      :value="display_value"
      @change="display_value=$event.target.value"
    ></textarea>
  </label>
</div>
`;

export const ScaleUi = {
  name: "scale-ui",
  props: ["field", "value", "num_datasets_in", "add_interactors"],
  computed: {
    dimensioned_value() {
      if (this.value != null) {
        return extend(true, [], this.value);
      }
      else {
        let default_value = (this.field.default != null) ? this.field.default : 1;
        return Array.from(Array(this.num_datasets_in)).map((x) => (default_value)).flat();
      }
    },
    display_value: {
      get() {
        return JSON.stringify(this.dimensioned_value, null, 2)
          //.replace(/^\[\s*/, '')
          //.replace(/\s*\]$/, '');
      },
      set(newValue) {
        try {
          let v = JSON.parse(newValue).map(x => (+x));
          this.$emit("change", this.field.id, v);
        }
        catch(e) {}
      }
    }
  },
  mounted: function () {
    // create the interactor here, if commanded
    if (this.add_interactors) {
      let chart = plotter.instance.active_plot;
      if (!chart) {return}
      let scales = this.dimensioned_value;
      let opts = {
        scales,
        point_size: 10
      }
      let scaler = new scaleInteractor(opts, null, null, d3);
      scaler.dispatch.on("update", () => {
        this.$emit("change", this.field.id, opts.scales);
      //   opts.scales.forEach((v,i) => this.$set(this.local_value, i, v));
        chart.update()
      });
      scaler.dispatch.on("end", () => {
        this.$emit("change", this.field.id, opts.scales);
      });
      // TODO: the update function is not implemented in the interactor,
      // so there's currently no way to push changes back to it.
      // ***
      //this.$watch('value', function(newVal, oldVal) {
      //  scaler.state.scales.splice(0, scaler.state.scales.length, ...newVal);
      //  chart.update();
      //});
      chart.interactors(scaler);
      chart.update();
      chart.do_autoscale();
      chart.resetzoom();
    }
  },
  template
}