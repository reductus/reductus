//import { json_patch } from '../libraries.js';

let template = `
<div class="plot-controls">
  <label v-if="plotnumber.show">
    dataset
    <input 
      type="number"
      v-model="plotnumber.value"
      :max="plotnumber.max"
      style="width:6em;"
      min="0"
      @change="plotNumberChange(plotnumber.value)"
    />
  </label>
  <template v-for="(axis, axis_name) in axes">
    <label v-if="axis.coord.show || axis.transform.show">
      {{axis_name}}
      <select 
        v-if="axis.coord.show"
        class="coord-select"
        v-model="axis.coord.value"
        @change="coordChange(axis_name, axis.coord.value)"
        >
        <option v-for="opt in axis.coord.options">
          {{opt}}
        </option>
      </select>
      <select 
        v-if="axis.transform.show"
        class="transform-select"
        v-model="axis.transform.value"
        @change="transformChange(axis_name, axis.transform.value)"
        >
        <option v-for="opt in axis.transform.options">
          {{opt}}
        </option>
      </select>
    </label>
  </template>
  <template v-for="(setting, setting_name) in settings">
    <label v-if="setting.show">
      {{setting_name}}
      <input
        type="checkbox"
        v-model="setting.value"
        @change="settingChange(setting_name, setting.value)"
        oldchange="$emit('settingChange', setting_name, setting.value)"/>
    </label>
  </template>
  <button v-if="download_svg.show" @click="$emit('downloadSVG')">&darr; svg</button>
  <button v-if="export_data.show" @click="$emit('export-data')">export</button>
  <label v-if="colormap.show">
    colormap
    <select
      class="colormap-select"
      v-model="colormap.value"
      @change="colormapChange(colormap.value)"
      >
      <option v-for="opt in colormap.options">
        {{opt}}
      </option>
    </select>
  </label>
</div>
`

const configurations = {
  twod: {
    x: 'linear',
    y: 'linear',
    z: ['linear', 'log'],
    colormap: true
  },
  nd: {
    x: ["linear", "log", "ln", "pow(2)", "pow(4)"],
    y: ["linear", "log", "ln", "pow(2)", "pow(4)"],
    z: false,
    colormap: false
  },
  oned: {

  }
}

function lookup(obj, name) {
  return name.split("/").reduce((sub, n) => sub[n], obj);
}

function update_descendants(obj, key, value) {
  // assume that all descendants are objects?
  if (key in obj) {
    obj[key] = value;
  }
  Object.entries(obj).forEach(([k,v]) => {
    if (v instanceof Object && !Array.isArray(v)) {
      update_descendants(v, key, value)
    }
  });
}

class Deferred {
  constructor() {
      this.promise = new Promise((resolve, reject) => {
          this.resolve = resolve;
          this.reject  = reject;
      });
  }
}

export const PlotControls = {
  name: "plot-controls",
  data: () => ({
    axes: {
      x: {
        coord: {
          value: 'x',
          options: ['x'],
          show: true
        },
        transform: {
          value: 'linear',
          options: ['linear', 'log'],
          show: true
        }
      },
      y: {
        coord: {
          value: 'v',
          options: ['v'],
          show: true
        },
        transform: {
          value: 'linear',
          options: ['linear', 'log'],
          show: true
        }
      },
      z: {
        coord: {
          value: 'z',
          options: ['z'],
          show: false
        },
        transform: {
          value: 'linear',
          options: ['linear', 'log'],
          show: false
        }
      }
    },
    settings: {
      grid: {
        value: true,
        show: false
      },
      errorbars: {
        value: true,
        show: true
      },
      points: {
        value: true,
        show: true
      },
      line: {
        value: true,
        show: true
      }
    },
    colormap: {
      show: false,
      value: 'jet',
      options: ['jet']
    },
    plotnumber: {
      show: false,
      value: 0,
      max: 0
    },
    download_svg: {show: true},
    export_data: {show: true}
  }),
  methods: {
    updateShow(names) {
      // mark every 'show' attribute below item as 'value'
      // first, hide everything:
      update_descendants(this.$data, 'show', false);
      // then show the selected items:
      names.forEach((n) => {
        let subobj = lookup(this, n);
        update_descendants(subobj, 'show', true);
      });
    },
    settingChange(setting_name, value) {},
    coordChange(axis_name, coord) {},
    transformChange(axis_name, transform) {},
  },
  mounted: function() { this.$emit("mounted") },
  template
}