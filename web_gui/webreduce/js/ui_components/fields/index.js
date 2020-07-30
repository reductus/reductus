import { d3, extend, rectangleSelect } from '../../libraries.js';
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
    let local_value;
    if (this.value != null) {
      local_value = extend(true, [], this.value);
    }
    else {
      local_value = Array.from(Array(this.num_datasets_in)).map((x) => []);
    }
    return {
      local_value,
      interaction: 'select'
    }
  },
  computed: {
    display_value: {
      get() {
        return prettyJSON(this.local_value);
        //.replace(/^\[\s*/, '')
        //.replace(/\s*\]$/, '');
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
    }
  },
  mounted: function () {
    // create the interactor here, if commanded
    if (this.add_interactors) {
      let chart = plotter.instance.active_plot;
      let selected = extend(true, [], this.local_value);
      let state = {
        selected,
      }
      var drag_instance = d3.drag();
      chart.svg.call(drag_instance);
      var selector = new rectangleSelect(drag_instance, null, null, d3);
      chart.interactors(selector);
      let interaction = () => (this.interaction); // make this into ref
      var update = (values) => {
        values.forEach((v,i) => {
          this.$set(this.local_value, i, v)
        });
        this.$emit("change", this.field.id, state.selected);
      }
      this.changed = () => {
        this.$emit('change', this.field.id, this.local_value);
        state.selected = extend(true, [], this.local_value);
        update_plot();
      }
      function update_plot() {
        chart.svg.selectAll("g.series").each(function (d, i) {
          // i is index of dataset
          let series_select = d3.select(this);
          let index_list = state.selected[i];
          series_select.selectAll("circle.dot")
            .classed("masked", function(dd,ii) { return index_list.includes(ii) });
        })
        chart.update();
      }

      update_plot();

      var onselect = function (xmin, xmax, ymin, ymax) {
        if (interaction() == 'zoom') {
          chart.x().domain([xmin, xmax]);
          chart.y().domain([ymin, ymax]);
          chart.update();
        }
        else {
          chart.svg.selectAll("g.series").each(function (d, i) {
            // i is index of dataset
            var series_select = d3.select(this);
            if (series_select.classed("hidden")) {
              // don't interact with hidden series.
              return
            }
            var index_list = state.selected[i];
            series_select.selectAll(".dot").each(function (dd, ii) {
              // ii is the index of the point in that dataset.
              var [x,y] = dd;
              if (x >= xmin && x <= xmax && y >= ymin && y <= ymax) {
                // manipulate data list directly:
                let index_index = index_list.indexOf(ii);
                let included = index_index > -1;
                if (included && interaction() != 'select') {
                  // then the index exists, but we're deselecting:
                  let index_index = index_list.indexOf(ii);
                  index_list.splice(index_index, 1);
                }
                else if (!included && interaction() == 'select') {
                  // then the index doesn't exist and we're selecting
                  index_list.push(ii);
                }
              }
            });
            index_list.sort();
          });
          // do update
          update(state.selected);
          update_plot();
        }
      }
      selector.callbacks(onselect);

      chart.svg.selectAll(".dot").on("click", null); // clear previous handlers
      chart.svg.selectAll("g.series").each(function (d, i) {
        let index_list = state.selected[i];
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
          }
          index_list.sort();
          update(state.selected);
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