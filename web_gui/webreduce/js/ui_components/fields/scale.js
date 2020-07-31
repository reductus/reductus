import { d3, extend, scaleInteractor } from '../../libraries.js';
import { plotter } from '../../plot.js';

let template = `
<div class="fields">
  <label>
    {{field.label}}
    <textarea
      :id="field.id"
      :placeholder="field.default"
      :rows="local_value.length+2"
      v-model="display_value"
      @change="$emit('change', field.id, local_value)"
    ></textarea>
  </label>
</div>
`;

export const ScaleUi = {
  name: "scale-ui",
  props: ["field", "value", "num_datasets_in", "add_interactors"],
  data: function () {
    let local_value;
    if (this.value != null) {
      local_value = extend(true, [], this.value);
    }
    else {
      let default_value = (this.field.default != null) ? this.field.default : 1;
      local_value = Array.from(Array(this.num_datasets_in)).map((x) => (default_value)).flat();
    }
    return { local_value }
  },
  computed: {
    display_value: {
      get() {
        return JSON.stringify(this.local_value, null, 2)
          //.replace(/^\[\s*/, '')
          //.replace(/\s*\]$/, '');
      },
      set(newValue) {
        //this.local_value = JSON.parse('[' + newValue + ']').map(x => (+x));
        this.local_value = JSON.parse(newValue).map(x => (+x));
      }
    }
  },
  mounted: function () {
    // create the interactor here, if commanded
    if (this.add_interactors) {
      let chart = plotter.instance.active_plot;
      let scales = [...this.local_value];
      let opts = {
        scales,
        point_size: 10
      }
      let scaler = new scaleInteractor(opts, null, null, d3);
      scaler.dispatch.on("updated", () => {
        opts.scales.forEach((v,i) => this.$set(this.local_value, i, v));
        chart.update()
      });
      scaler.dispatch.on("end", () => {
        this.$emit("change", this.field.id, opts.scales);
      });
      chart.interactors(scaler);
      chart.update();
      chart.do_autoscale();
      chart.resetzoom();
    }
  },
  template
}