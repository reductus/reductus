let dataflow_template = `
<svg class="dataflow">
  <defs>
    <filter id="glow" filterUnits="objectBoundingBox" x="-50%" y="-50%" width="200%" height="200%">
      <feOffset result="offOut" in="SourceGraphic" dx="0" dy="0" />
      <feColorMatrix in="offOut" result="matrixOut" type="matrix"
        values="0 0 0 0 0 \
                1 1 1 1 0 \
                0 0 0 0 0 \
                0 0 0 1 0" />
      <feGaussianBlur in="matrixOut" result="blurOut" stdDeviation="10" />
      <feBlend in="SourceGraphic" in2="blurOut" mode="normal" />
    </filter>
    <pattern id="output_hatch" patternUnits="userSpaceOnUse" width=10 height=10 >
      <path 
        d="M-1,1 l2,-2 M0,10 l10,-10 M9,11 l2,-2"
        style="stroke:#88FFFF;stroke-opacity:1;stroke-width:3;"
      />
    </pattern>
    <pattern id="input_hatch" patternUnits="userSpaceOnUse" width=10 height=10 >
      <path 
        d="M-1,1 l2,-2 M0,10 l10,-10 M9,11 l2,-2"
        style="stroke:#88FF88;stroke-opacity:1;stroke-width:3;"
      />
    </pattern>
  </defs>
  <g class="dataflow-template">
    <module 
      v-for="(module_data, index) in template_data.modules" 
      ref="modules" 
      :module_index="index"
      :module_def="instrument_def.find((m) => (m.id == module_data.module))"
      :transform="'translate('+ module_data.x + ',' + module_data.y + ')'" 
      :module_data="module_data"
      :selected="selected"
      :options="options"
      v-on="$listeners"
    >
    </module>
    <path
      v-if="options.wire_background"
      v-for="wire_data in template_data.wires"
      :d="pathstring(wire_data)"
      class="wire-background">
    </path>
    <path
      v-for="wire_data in template_data.wires"
      :d="pathstring(wire_data)"
      class="wire">
    </path>
  </g>
</svg>
`;

  let module_template =`
  <g class="module" style="cursor: move;">
    <g class="title" :class="{selected: selected.modules.includes(module_index)}">
        <text ref="title_text" class="title text" x="5" y="5" dy="1em">{{module_data.title}}</text>
        <rect 
          class="title border"
          :width="display_width"
          :height="options.terminal.height"
          x="0"
          y="0"
          @click="$emit('module-clicked', module_index, module_def.inputs[0])">
        </rect>
    </g>
    <g v-for="(def,index) in module_def.inputs" 
      class="terminals inputs"
      :class="{selected: (selected.terminals.findIndex(([ii, id]) => (ii == module_index && id == def.id)) > -1)}"
      :ref="def.id"
      :transform="'translate(-' + options.terminal.width + ',' + (index * options.terminal.height) + ')'"
      >

      <text class="input label" x="5" y="5" dy="1em">{{def.label.toLowerCase()}}</text>
      <rect 
        class="terminal input" 
        :width="options.terminal.width"
        :height="options.terminal.height"
        :terminal_id="def.id.toLowerCase()"
        :style="{fill: 'url(#input_hatch)'}"
        @click="$emit('terminal-clicked', module_index, def.id.toLowerCase(), $event.ctrlKey, $event.shiftKey)"
        >
        <title>{{def.label.toLowerCase()}}</title>
      </rect>
      <polygon class="terminal input state" points="0,0 20,15 0,30"></polygon>
    </g>
    
    <g v-for="(def,index) in module_def.outputs"
      :key="module_index.toFixed() + ':' + def.id"
      class="terminals outputs"
      :class="{selected: (selected.terminals.findIndex(([ii, id]) => (ii == module_index && id == def.id)) > -1)}"
      :ref="def.id"
      :transform="'translate(' + display_width + ',' + (index * options.terminal.height) + ')'">
      <text class="output label" x="5" y="5">{{def.label.toLowerCase()}}</text>
      <rect 
        class="terminal output" 
        :width="options.terminal.width" 
        :height="options.terminal.height" 
        :terminal_id="def.id.toLowerCase()"
        @click="$emit('terminal-clicked', module_index, def.id.toLowerCase(), $event.ctrlKey, $event.shiftKey)"
        >
          <title>{{def.label.toLowerCase()}}</title>
      </rect>
      <polygon class="terminal input state" points="0,0 20,15 0,30"></polygon>
    </g>      
  </g>
`;

const Module = {
  name: "module",
  props: ["module_def", "module_data", "module_index", "options", "selected"],
  computed: {
    display_width: function () {
      return (this.module_data.text_width != null) ? this.module_data.text_width : this.options.default_text_width;
    }
  },
  template: module_template
}

export const DataflowViewer = {
  name: "dataflow-viewer",
  components: { "module": Module },
  props: ["instrument_def", "template_data", "selected"],
  data: () => ({
    options: {
      autosize_modules: false,
      padding: 5,
      default_text_width: 85,
      wire_background: true,
      terminal: {
        width: 20,
        height: 30
      }
    }
  }),
  methods: {
    module_select(index, first_input) {
      this.selected.modules.splice(0, this.selected.modules.length, index);
      if (first_input != null) {
        this.selected.terminals.splice(0, this.selected.terminals.length, [index, first_input.id]);
      }
      else {
        this.selected.terminals.splice(0);
      }
    },
    terminal_select(index, terminal_id, ctrlKey, shiftKey) {
      if (ctrlKey || shiftKey) {
        this.selected.modules.splice(0);
        let item_index = this.selected.terminals.findIndex(([ii, id]) => (ii == index && id == terminal_id));
        if (item_index > -1) {
          this.selected.terminals.splice(item_index, 1);
        }
        else {
          this.selected.terminals.push([index, terminal_id]);
        }
      }
      else {
        this.selected.terminals.splice(0, this.selected.terminals.length, [index, terminal_id]);
        this.selected.modules.splice(0, this.selected.modules.length, index);
      }
    },
    pathstring: function (wire_data) {
      let source = wire_data.source;
      let target = wire_data.target;
      let source_module = this.template_data.modules[source[0]];
      let target_module = this.template_data.modules[target[0]];
      let source_def = this.instrument_def.find((s) => (s.id == source_module.module));
      let target_def = this.instrument_def.find((s) => (s.id == target_module.module));
      let source_terminal_index = source_def.outputs.findIndex((t) => (t.id == source[1]));
      let target_terminal_index = target_def.inputs.findIndex((t) => (t.id == target[1]));

      let s = {
        x: source_module.x + (source_module.text_width || this.options.default_text_width) + this.options.terminal.width,
        y: source_module.y + (this.options.terminal.height * (source_terminal_index + 0.5))
      }
      let t = {
        x: target_module.x - this.options.terminal.width,
        y: target_module.y + (this.options.terminal.height * (target_terminal_index + 0.5))
      }

      return makeConnector(s, t);
    }
  },
  template: dataflow_template
}

var wirecurve = 0.67;

function makeConnector(pt1, pt2) {
  let d = "M";
  let dx = Math.abs(+pt1.x - +pt2.x),
    dy = Math.abs(+pt1.y - +pt2.y);
  d = "M" + pt1.x + "," + pt1.y + " ";
  d += "C" + (+pt1.x + wirecurve * dx).toFixed() + "," + pt1.y + " ";
  d += (+pt2.x - wirecurve * dx).toFixed() + "," + pt2.y + " ";
  d += pt2.x + "," + pt2.y;
  return d;
}