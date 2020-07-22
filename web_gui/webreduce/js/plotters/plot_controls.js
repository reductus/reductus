let template = `
<div class="plot-controls">
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
    <label>
      {{setting_name}}
      <input
        type="checkbox"
        v-model="setting.value"
        @change="settingChange(setting_name, setting.value)"
        oldchange="$emit('settingChange', setting_name, setting.value)"/>
    </label>
  </template>
  <button @click="$emit('downloadSVG')">&darr; svg</button> 
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
    }
  }),
  methods: {
    settingChange(setting_name, value) {},
    coordChange(axis_name, coord) {},
    transformChange(axis_name, transform) {},
  },
  template
}