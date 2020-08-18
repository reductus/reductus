import { d3, extend, rectangleSelectPoints } from '../../libraries.js';
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
      @change="changed"
    ></textarea>
  </label>
  <div v-if="add_interactors">
    <label 
      v-for="opt in ['zoom', 'select', 'deselect']" 
      style="border:1px solid grey;border-radius:2px;"
      >
      <input type="radio" name="interaction" :value="opt" v-model="interaction"/>
     {{opt}}
    </label>
  </div>
  </select>
</div>
`;

export const IndexUi = {
  name: "index-ui",
  props: ["field", "value", "num_datasets_in", "add_interactors"],
  data: function () {
    let local_value = this.getLocal(this.value)
    return {
      local_value,
      interaction: 'select'
    }
  },
  computed: {
    display_value: {
      get() {
        return prettyJSON(this.local_value);
      },
      set(newValue) {
        //this.local_value = JSON.parse('[' + newValue + ']').map(x => (+x));
        let parsed = JSON.parse(newValue);
        parsed.forEach((v,i) => this.$set(this.local_value, i, v));
      }
    }
  },
  methods: {
    changed: function() {
      this.$emit('change', this.field.id, this.local_value);
    },
    getLocal(value) {
      let value_length = (this.value || []).length;
      if (this.value != null && this.num_datasets_in != value_length) {
        alert(`${value_length} index values defined for ${this.num_datasets_in} datasets; 
        Extending with empty values or truncating to match data length`);
      }
      return Array.from(Array(this.num_datasets_in)).map((x,i) => 
          ((this.value || [])[i] || []));
    },
    setLocal() {}
  },
  mounted: function () {
    // create the interactor here, if commanded
    if (this.add_interactors) {
      let chart = plotter.instance.active_plot;
      if (!chart) { return } // bail out
      var selected = extend(true, [], this.local_value);
      let state = {
        skip_points: false
      }

      var update = (values) => {
        values.forEach((v,i) => {
          this.$set(this.local_value, i, v)
        });
        this.$emit("change", this.field.id, this.local_value);
      }
      this.changed = () => {
        this.$emit('change', this.field.id, this.local_value);
        selected = extend(true, [], this.local_value);
        update_plot();
      }
      function update_plot() {
        chart.svg.selectAll("g.series").each(function (d, i) {
          // i is index of dataset
          let series_select = d3.select(this);
          let index_list = selected[i];
          series_select.selectAll("circle.dot")
            .classed("masked", function(dd,ii) { return index_list.includes(ii) });
        })
        chart.update();
      }

      let selector = new rectangleSelectPoints(state, null, null, d3);
      chart.interactors(selector);
      // TODO: make this.interaction into ref?
      let that = this; 
      selector.dispatch.on("selection", function() {
        let mode = that.interaction;
        if (mode == 'zoom') {
          chart.x().domain([this.limits.xmin, this.limits.xmax]);
          chart.y().domain([this.limits.ymin, this.limits.ymax]);
          chart.update();
        }
        else if (mode == 'select') {
          for (let i in selected) {
            selected[i] = [...selected[i], ...this.indices[i]];
            selected[i].sort();
          }
          update(selected);
          update_plot();
        }
        else if (mode == 'deselect') {
          for (let i in selected) {
            let to_remove = this.indices[i];
            selected[i] = selected[i].filter((ii) => (!to_remove.includes(ii)));
          }
          update(selected);
          update_plot();
          update
        }

      })
      
      update_plot();

      chart.svg.selectAll(".dot").on("click", null); // clear previous handlers
      chart.svg.selectAll("g.series").each(function (d, i) {
        let index_list = selected[i];
        d3.select(this).selectAll('.dot').on('click', (dd,ii) => {
          d3.event.stopPropagation();
          d3.event.preventDefault();
          let index_index = index_list.indexOf(ii);
          let included = index_index > -1;
          if (included) {
            index_list.splice(index_index, 1);
          }
          else {
            index_list.push(ii);
            index_list.sort();
          }
          update(selected);
          update_plot();
        });
      });
    }
  },
  template
}

function prettyJSON(d) {
  return "[\n  " + d.map(JSON.stringify).join(",\n  ") + "\n]"
}