import { extend } from '../libraries.js';

let dataflow_template = `
<div 
  class="dataflow editor container"
  @contextmenu.prevent="contextmenu"
  @mousedown.left="mousedown"
  >
  <md-menu md-size="auto"
    :md-active.sync="menu.visible"
    :style="{height: 0}"
    :md-offset-x="menu.x"
    :md-offset-y="menu.y"
    md-direction="bottom-start">
    <md-button style="visibility:hidden"></md-button>

    <md-menu-content>
      <md-menu-item v-if="menu.startdata == null">
          <select name="add_module" id="add_module" @change="add_module">
            <option value="" disabled="true" selected="true">Add module:</option>
            <option v-for="module in instrument_def.modules" :value="module.id">{{module.name}}</option>
          </select>
      </md-menu-item>
      <md-menu-item v-if="menu.startdata == null && menu.clipboard != null">
        <md-button @click="paste_module();menu.visible=false;" class="md-raised md-primary">Paste</md-button>
      </md-menu-item>
      <md-menu-item v-if="false && menu.startdata == null">
        <md-field>
          <label for="add_module">Add Module Here</label>
          <md-select name="add_module" id="add_module" @md-selected="add_module">
            <md-option v-for="module in instrument_def.modules" :value="module.id">{{module.name}}</md-option>
          </md-select>
        </md-field>
      </md-menu-item>
      <md-menu-item v-if="menu?.startdata?.module_index !== undefined">
        <md-button  @click="copy_module(menu.startdata.module_index);menu.visible=false;" class="md-raised md-primary">Copy</md-button>
      </md-menu-item>
      <md-menu-item v-if="menu?.startdata?.module_index !== undefined">
        <md-button @click="remove_module(menu.startdata.module_index);menu.visible=false;" class="md-accent md-raised">Delete</md-button>
      </md-menu-item>
      <md-menu-item v-if="menu?.startdata?.module_index !== undefined">
        <md-button @click="rename_module(menu.startdata.module_index);menu.visible=false;" class="md-raised">Rename</md-button>
      </md-menu-item>
      <md-menu-item v-if="menu.startdata != null && menu.startdata.target_type==='wire'">
        <md-button @click="remove_wire(menu.startdata.wire_index);menu.visible=false;" class="md-accent md-raised">Delete wire</md-button>
      </md-menu-item>
    </md-menu-content>
  </md-menu>

  <svg class="dataflow editor" ref="svg">
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
        <rect width="10" height="10" x="0" y="0" fill="#FFFFFF" />
        <path 
          d="M-1,1 l2,-2 M0,10 l10,-10 M9,11 l2,-2"
          style="stroke:#88FFFF;stroke-opacity:1;stroke-width:3;"
        />
      </pattern>
      <pattern id="input_hatch" patternUnits="userSpaceOnUse" width=10 height=10 >
        <rect width="10" height="10" x="0" y="0" fill="#FFFFFF" />
        <path 
          d="M-1,1 l2,-2 M0,10 l10,-10 M9,11 l2,-2"
          style="stroke:#88FF88;stroke-opacity:1;stroke-width:3;"
        />
      </pattern>
    </defs>
    <g class="dataflow-template" ref="template">
      <module 
        v-for="(module_data, index) in template_data.modules"
        :key="index"
        ref="modules" 
        :module_index="index"
        :module_def="module_defs[module_data.module]"
        :transform="'translate('+ module_data.x + ',' + module_data.y + ')'" 
        :module_data="module_data"
        :selected="selected"
        :moving="drag.modules.includes(index)"
        :new_wire="drag.new_wire"
        :satisfied="satisfied"
        :options="options"
        @startdata="set_startdata"
        @enddata="set_enddata"
        @clicked="clicked"
        v-on="$listeners"
      >
      </module>
      <template v-for="(wire_data, wire_index) in template_data.wires">
        <path
          v-if="options.wire_background"
          :d="pathstring(wire_data)"
          :class="{satisfied: satisfied.wires.includes(wire_index)}"
          class="wire-background"
          @mousedown="set_startdata({target_type:'wire', wire_index})"
          >
        </path>
        <path
          :d="pathstring(wire_data)"
          :class="{satisfied: satisfied.wires.includes(wire_index)}"
          class="wire"
          @mousedown="set_startdata({target_type:'wire', wire_index})"
          >
        </path>
      </template>
      <path
        v-if="drag.new_wire"
        :d="pathstring(drag.new_wire)"
        class="wire-new"
        oldstyle="stroke:#000000;stroke-opacity:0.3;pointer-events:none"
        >
      </path>
    </g>
    <rect
      :class="{'select_many': true}"
      :width="Math.abs(select_many.x0 - select_many.x1)"
      :height="Math.abs(select_many.y0 - select_many.y1)"
      :display="(select_many.active) ? 'inline' : 'none'"
      fill="grey"
      fill-opacity="40%"
      :x="Math.min(select_many.x0, select_many.x1)"
      :y="Math.min(select_many.y0, select_many.y1)"
      />
    </rect>
  </svg>
  <md-dialog id="help" :md-active.sync="menu.help_visible" style="max-width:768px;">
    <md-dialog-title>Using the Template Panel</md-dialog-title>
      <md-tabs md-dynamic-height>
        <md-tab md-label="Editing">
          <p>Left-click and drag a module to move it</p>
          <p>Right-click a module or wire and you will have the option to delete or copy</p>
          <p>Left-click and then drag on a terminal (input or output) to create a new wire.  
          Stop over the opposite type of terminal to finish the connection</p>
          <p>Shift-left-click to or Ctrl-drag to highlight multiple modules, then:</p>
          <ul>
            <li>left-click and drag them together</li>
            <li>right-click to copy or delete them all at once</li>
          </ul>
          <p>Right-click on an empty spot in the template to add a new module or paste a copied module or group of modules</p>
        </md-tab>
        <md-tab md-label="Operating">
          <p>Left-click on a module to select and show/edit its parameters (first input terminal also autoselected)</p>
          <p>Select module with datafile fields (fileinfo) to show filebrowser</p>
          <p>Left-click on a terminal to plot its data (module is autoselected)</p>
          <p>Shift-left-click on multiple terminals to compare data (if compatible for plotting)</p>
        </md-tab>
      </md-tabs>
  </md-dialog>
</div>
`;

let module_template = `
  <g class="module" style="cursor: move;">
    <g class="title" :class="{selected: selected.modules.includes(module_index), moving}">
        <text ref="title_text" class="title text" x="5" y="5" dy="1em">{{module_data.title}}</text>
        <rect 
          class="title border"
          :width="display_width"
          :height="options.terminal.height"
          x="0"
          y="0"
          @mousedown="$emit('startdata', {target_type:'module', module_index, module_data, module_def, terminal_def: module_def.inputs[0] || {}, ctrlKey: $event.ctrlKey, shiftKey: $event.shiftKey})"
        >
        </rect>
    </g>
    <g v-for="(terminal_def,index) in module_def.inputs"
      :key="module_index.toFixed() + ':' + terminal_def.id"
      class="terminals inputs"
      :class="{selected: (selected.terminals.findIndex(([ii, id]) => (ii == module_index && id == terminal_def.id)) > -1),
               satisfied: satisfied.terminals.findIndex(([ii, id]) => (ii == module_index && id == terminal_def.id)) > -1,
               wireable: new_wire && 'x' in new_wire.target}"
      :ref="terminal_def.id"
      :transform="'translate(-' + options.terminal.width + ',' + (index * options.terminal.height) + ')'"
      >

      <text class="input label" x="5" y="5" dy="1em">{{terminal_def.label.toLowerCase()}}</text>
      <rect 
        class="terminal input" 
        :width="options.terminal.width"
        :height="options.terminal.height"
        :terminal_id="terminal_def.id.toLowerCase()"
        @mousedown="$emit('startdata', {target_type:'input-terminal', module_index, module_data, module_def, terminal_def, ctrlKey: $event.ctrlKey, shiftKey: $event.shiftKey})"
        @mouseup="$emit('enddata', {target_type:'input-terminal', module_index, module_data, module_def, terminal_def, ctrlKey: $event.ctrlKey, shiftKey: $event.shiftKey})"
        >
        <title>{{terminal_def.label.toLowerCase()}}</title>
      </rect>
      <polygon class="terminal input state" points="0,0 20,15 0,30"></polygon>
    </g>
    
    <g v-for="(terminal_def,index) in module_def.outputs"
      :key="module_index.toFixed() + ':' + terminal_def.id"
      class="terminals outputs"
      :class="{selected: (selected.terminals.findIndex(([ii, id]) => (ii == module_index && id == terminal_def.id)) > -1),
               satisfied: satisfied.modules.includes(module_index),
               wireable: new_wire && 'x' in new_wire.source }"
      :ref="terminal_def.id"
      :transform="'translate(' + display_width + ',' + (index * options.terminal.height) + ')'">
      <text class="output label" x="5" y="5">{{terminal_def.label.toLowerCase()}}</text>
      <rect 
        class="terminal output" 
        :width="options.terminal.width" 
        :height="options.terminal.height" 
        :terminal_id="terminal_def.id.toLowerCase()"
        @mousedown="$emit('startdata', {target_type:'output-terminal', module_index, module_data, module_def, terminal_def, ctrlKey: $event.ctrlKey, shiftKey: $event.shiftKey})"
        @mouseup="$emit('enddata', {target_type:'output-terminal', module_index, module_data, module_def, terminal_def, ctrlKey: $event.ctrlKey, shiftKey: $event.shiftKey})"
        >
          <title>{{terminal_def.label.toLowerCase()}}</title>
      </rect>
      <polygon class="terminal output state" points="0,0 20,15 0,30"></polygon>
    </g>      
  </g>
`;

const Module = {
  name: "module",
  props: ["module_def", "module_data", "module_index", "options", "selected", "satisfied", "moving", "new_wire"],
  methods: {
    set_display_width: function () {
      let bbox = this.$refs.title_text.getBBox();
      this.$set(this.module_data, 'text_width', Math.round(bbox.width) + 10)
    }
  },
  computed: {
    display_width: function () {
      return Math.max(this.module_data.text_width ?? 0, this.options.default_text_width);
    }
  },
  template: module_template
}

export const DataflowViewer = {
  name: "dataflow-viewer",
  components: { "module": Module },
  props: ["instrument_def"],
  data: () => ({
    template_data: {
      modules: [],
      wires: []
    },
    menu: {
      visible: false,
      help_visible: false,
      x: 0,
      y: 0,
      data: null,
      module_to_add: null,
      modules_to_delete: [],
      wires_to_delete: []
    },
    selected: {
      modules: [],
      terminals: []
    },
    select_many: {
      started: false,
      active: false,
      x0: 0,
      y0: 0,
      x1: 0,
      y1: 0,
      module_positions: [],
      previously_selected: []
    },
    satisfied: {
      modules: [],
      terminals: [],
      wires: []
    },
    drag: {
      modules: [],
      svgPoint: null,
      active: false,
      buttons: null,
      startdata: null,
      enddata: null,
      new_wire: null
    },
    options: {
      move: {
        x_step: 10,
        y_step: 10
      },
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
  computed: {
    module_defs: function () {
      return Object.fromEntries((this.instrument_def.modules || []).map(m => (
        [m.id, m]
      )));
    }
  },
  methods: {
    module_select(module_index, first_input, ctrlKey, shiftKey) {
      if (ctrlKey || shiftKey) {
        // selecting modules for moving
        let item_index = this.drag.modules.indexOf(module_index);
        if (item_index > -1) {
          this.drag.modules.splice(item_index, 1);
        }
        else {
          this.drag.modules.push(module_index);
        }
      }
      else {
        // selecting modules
        this.drag.modules.splice(0);
        this.selected.modules.splice(0, this.selected.modules.length, module_index);
        if (first_input != null) {
          this.selected.terminals.splice(0, this.selected.terminals.length, [module_index, first_input.id]);
        }
        else {
          this.selected.terminals.splice(0);
        }
        this.on_select();
      }
    },
    terminal_select(index, terminal_def, ctrlKey, shiftKey) {
      this.drag.modules.splice(0);
      let terminal_id = terminal_def.id;
      if (ctrlKey || shiftKey) {
        // selecting terminals for multi-plot
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
      this.on_select();
    },
    pathstring: function (wire_data) {
      let source = wire_data.source;
      let target = wire_data.target;

      let s;
      if (source.x == null && source.y == null) {
        let source_module = this.template_data.modules[source[0]];
        let source_def = this.module_defs[source_module.module];
        let source_terminal_index = source_def.outputs.findIndex((t) => (t.id == source[1]));
        s = {
          x: source_module.x + Math.max(source_module.text_width ?? 0, this.options.default_text_width) + this.options.terminal.width,
          y: source_module.y + (this.options.terminal.height * (source_terminal_index + 0.5))
        }
      }
      else {
        s = source;
      }

      let t;
      if (target.x == null && target.y == null) {
        let target_module = this.template_data.modules[target[0]];
        let target_def = this.module_defs[target_module.module];
        let target_terminal_index = target_def.inputs.findIndex((t) => (t.id == target[1]));
        t = {
          x: target_module.x - this.options.terminal.width,
          y: target_module.y + (this.options.terminal.height * (target_terminal_index + 0.5))
        }
      }
      else {
        t = target;
      }
      return makeConnector(s, t);
    },
    set_startdata: function (data) {
      this.drag.startdata = data;
    },
    set_enddata: function (data) {
      this.drag.enddata = data;
    },
    clicked: function (data) {
      if (!data) {
        this.drag.modules.splice(0);
        return
      }
      if (data.target_type == "module") {
        this.module_select(data.module_index, data.terminal_def, data.ctrlKey, data.shiftKey);
      }
      else if (/terminal$/.test(data.target_type)) {
        this.terminal_select(data.module_index, data.terminal_def, data.ctrlKey, data.shiftKey);
      }
    },
    contextmenu: function (ev) {
      const { x, y } = this.getSVGCoords(ev);
      const d = this.drag;

      this.$emit('contextmenu', d.startdata, x, y);
      this.menu.startdata = d.startdata;
      this.menu.x = x;
      this.menu.y = y;
      this.menu.visible = true;
      d.start_x = null;
      d.start_y = null;
      d.startdata = null;
      d.enddata = null;
      d.started = false;
      d.active = false;
      d.new_wire = null;
    },
    add_module: function (ev) {
      let to_add = ev.target.value;
      this.template_data.modules.push({
        module: to_add,
        title: this.module_defs[to_add].name,
        x: this.menu.x,
        y: this.menu.y
      });
      this.menu.visible = false;
    },
    remove_wire(index) {
      this.template_data.wires.splice(index, 1);
      this.on_change();
    },
    remove_module(index) {
      let indices = [index];
      if (this.drag.modules.includes(index)) {
        indices = [...this.drag.modules];
        this.drag.modules.splice(0);
      }
      let wires = this.template_data.wires;
      indices.sort((a,b) => (a - b)).reverse();
      let old_order = this.template_data.modules.map((m, i) => (i));
      for (let mi of indices) {
        this.template_data.modules.splice(mi, 1);
        old_order.splice(mi, 1);
      }
      for (let wi = wires.length - 1; wi >= 0; wi--) {
        let w = wires[wi];
        let new_source = old_order.indexOf(w.source[0]);
        let new_target = old_order.indexOf(w.target[0]);
        if (new_source < 0 || new_target < 0) {
          wires.splice(wi, 1);
        }
        else {
          w.source[0] = new_source;
          w.target[0] = new_target;
        }
      }

      let sm = this.selected.modules;
      for (let si = sm.length - 1; si >= 0; si--) {
        let new_selected = old_order.indexOf(sm[si]);
        if (new_selected < 0) {
          sm.splice(si, 1);
        }
        else {
          sm.splice(si, 1, new_selected)
        }
      }

      let st = this.selected.terminals;
      for (let si = st.length - 1; si >= 0; si--) {
        let new_selected = old_order.indexOf(st[si][0]);
        if (new_selected < 0) {
          st.splice(si, 1);
        }
        else {
          st[si][0] = new_selected;
        }
      }

      //console.log(JSON.stringify(this.template_data.wires, null, 2));
      this.on_change();
    },
    copy_module(index) {
      let indices = [index];
      if (this.drag.modules.includes(index)) {
        indices = [...this.drag.modules];
      }
      // find all wires that are within the copied group,
      // and duplicate their contents
      let wires = this.template_data.wires
        .filter((w) => (indices.includes(w.source[0]) && indices.includes(w.target[0])))
        .map((w) => (extend(true, {}, w)));

      wires.forEach((w, i) => {
        let new_source = indices.indexOf(w.source[0]);
        let new_target = indices.indexOf(w.target[0]);
        w.source[0] = new_source;
        w.target[0] = new_target;
      })

      let modules = indices.map((mi) => (extend(true, {}, this.template_data.modules[mi])));
      let reference_point = { x: this.menu.x, y: this.menu.y };
      this.menu.clipboard = { modules, wires, reference_point };
    },
    rename_module(index) {
      let module = this.template_data.modules[index];
      let new_title = prompt("Enter new name:", module.title);
      if (new_title != null) {
        module.title = new_title;
      }
      this.$nextTick(() => this.$refs.modules[index].set_display_width());
    },
    paste_module() {
      let { modules, wires, reference_point } = this.menu.clipboard;
      let relative_x = this.menu.x - reference_point.x;
      let relative_y = this.menu.y - reference_point.y;
      let new_modules = modules.map((m) => (extend(true, {}, m)));
      let new_wires = wires.map((w) => (extend(true, {}, w)));
      let module_offset = this.template_data.modules.length;
      new_modules.forEach((m) => { m.x += relative_x; m.y += relative_y });
      new_wires.forEach((w) => { w.source[0] += module_offset; w.target[0] += module_offset; });
      this.template_data.modules.splice(module_offset, 0, ...new_modules);
      this.template_data.wires.splice(this.template_data.wires.length, 0, ...new_wires);
      let new_selection = new_modules.map((m, i) => (i + module_offset));
      this.drag.modules.splice(0, this.drag.modules.length, ...new_selection);
      this.on_change();
    },
    mousedown: function (ev) {
      document.addEventListener('mouseup', this.mouseup);
      document.addEventListener('mousemove', this.mousemove);
      let d = this.drag;
      let s = this.select_many;
      if (d.started == true || s.started == true) {
        // then we're already dragging.  Ignore other mouse buttons.
        return
      }
      if (ev.shiftKey || ev.ctrlKey) {
        // then begin a select_many operation
        s.started = true;
        const svgCoords = this.getSVGCoords(ev);
        const module_positions = this.$refs.modules.map((m) => ({
          x: m.module_data.x,
          y: m.module_data.y,
          width: m.display_width,
          height: m.options.terminal.height
        }));
        s.x0 = svgCoords.x;
        s.y0 = svgCoords.y;
        s.x1 = svgCoords.x;
        s.y1 = svgCoords.y;
        s.module_positions = module_positions;
        s.previously_selected = [...d.modules];
      }
      else {
        d.module_start_positions = this.template_data.modules.map((m) => ({ x: m.x, y: m.y }));
        if (d.startdata && d.startdata.target_type == 'module') {
          let dmodules = this.drag.modules;
          d.to_move = (dmodules.includes(d.startdata.module_index)) ? dmodules : [d.startdata.module_index];
        }
        else {
          d.to_move = [];
        }
        if (d.startdata && /terminal$/.test(d.startdata.target_type)) {
          // make a new wire!
        }
        d.started = true;
        d.start_ev = ev;
        d.start_x = ev.x;
        d.start_y = ev.y;
        d.delta_x = 0;
        d.delta_y = 0;
        d.buttons = ev.buttons;
        d.new_wire = null;
      }
      //console.log(JSON.stringify(d));
    },
    mouseup: function (ev) {
      document.removeEventListener('mouseup', this.mouseup);
      document.removeEventListener('mousemove', this.mousemove);
      const d = this.drag;
      const s = this.select_many;
      if (ev.buttons != 0) {
        // if some reprobate has pushed and release a different button
        // during a drag...
        return
      }
      if (d.active) {
        if (d.new_wire != null) {
          // then we're dragging a wire... the last one
          let wires = this.template_data.wires;
          let wire = d.new_wire;
          let compatible = true;
          if (wire.loose_end == wire.source && d.enddata && d.enddata.target_type == 'output-terminal') {
            wire.source = [d.enddata.module_index, d.enddata.terminal_def.id];
          }
          else if (wire.loose_end == wire.target && d.enddata && d.enddata.target_type == 'input-terminal') {
            wire.target = [d.enddata.module_index, d.enddata.terminal_def.id];
          }
          else {
            // incompatible landing spot
            compatible = false;
            console.warn("can't wire to here...");
          }
          let is_duplicate = this.template_data.wires.findIndex((w) => (
            w.source[0] == wire.source[0] &&
            w.source[1] == wire.source[1] &&
            w.target[0] == wire.target[0] &&
            w.target[1] == wire.target[1]
          )) > -1;
          let is_self = (wire.target[0] == wire.source[0]);
          if (is_duplicate) {
            console.warn("duplicate wire: not adding")
          }
          if (is_self) {
            console.warn("wire source and target are the same module: not adding");
          }
          // if all is well, add the wire!
          if (compatible && !is_duplicate && !is_self) {
            wires.push({ source: wire.source, target: wire.target });
            this.on_change();
          }
        }
      }
      else if (s.active) {
        // console.log('s.active', s);
      }
      else {
        this.clicked(d.startdata);
      }

      d.start_x = null;
      d.start_y = null;
      d.startdata = null;
      d.enddata = null;
      d.started = false;
      d.active = false;
      d.new_wire = null;

      s.started = false;
      s.active = false;
      s.previously_selected = [];

    },
    mousemove: function (ev) {
      let d = this.drag;
      let s = this.select_many;
      const svgCoords = this.getSVGCoords(ev);
      // drag stuff
      const dx = this.options.move.x_step;
      const dy = this.options.move.y_step;
      const new_delta_x = dx * Math.round((ev.x - d.start_x) / dx);
      const new_delta_y = dy * Math.round((ev.y - d.start_y) / dy);
      const active =  (new_delta_x != d.delta_x || new_delta_y != d.delta_y);
      if (d.started && d.buttons == 1) {
        if (active) {
          d.active = true;
          d.delta_x = new_delta_x;
          d.delta_y = new_delta_y;
          if (d.startdata == null) {

          }
          else if (d.startdata.target_type == 'module') {
            d.to_move.forEach((module_index) => {
              let sp = d.module_start_positions[module_index];
              let m = this.template_data.modules[module_index];
              m.x = sp.x + new_delta_x;
              m.y = sp.y + new_delta_y;
            });
            this.$emit('dragged', d.startdata);
          }
          else if (/terminal$/.test(d.startdata.target_type)) {
            // start wiring
            if (d.new_wire == null) {
              let loose_end = { x: svgCoords.x, y: svgCoords.y };
              let new_wire = { loose_end };
              d.new_wire = new_wire;
              if (/^output/.test(d.startdata.target_type)) {
                new_wire.source = [d.startdata.module_index, d.startdata.terminal_def.id];
                new_wire.target = loose_end;
              }
              else {
                new_wire.target = [d.startdata.module_index, d.startdata.terminal_def.id];
                new_wire.source = loose_end;
              }
            }
            else {
              d.new_wire.loose_end.x = svgCoords.x;
              d.new_wire.loose_end.y = svgCoords.y;
            }
          }
        }
      }
      else if (s.started) {
        if (active) {
          s.active = true;
          s.x1 = svgCoords.x;
          s.y1 = svgCoords.y;
          const selected = getSelected(s);
          this.drag.modules = selected;
        }
      }
    },
    getSVGCoords: function (ev) {
      this.drag.svgPoint.x = ev.clientX;
      this.drag.svgPoint.y = ev.clientY;
      return this.drag.svgPoint.matrixTransform(this.$refs.svg.getScreenCTM().inverse());
    },
    get_bbox() {
      return this.$refs.template.getBBox();
    },
    on_select: function () { },
    on_change: function () { /* override as needed */ },
    fit_module_text: function () {
      this.$refs.modules.forEach((m) => {
        m.set_display_width();
      })
    }
  },
  mounted: function () {
    this.drag.svgPoint = this.$refs.svg.createSVGPoint();
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

function getSelected(select_many) {
  const { x0, y0, x1, y1, module_positions } = select_many;
  const [ xmin, xmax ] = [ x0, x1 ].sort((a,b) => ( a - b ));
  const [ ymin, ymax ] = [ y0, y1 ].sort((a,b) => ( a - b ));
  const new_selection = module_positions.map((p, i) => (
    ( p.x <= xmax &&
      p.x + p.width >= xmin &&
      p.y <= ymax &&
      p.y + p.height >= ymin
    ) ? i : false
  )).filter((indexish) => indexish !== false)

  const selected_union = new Set([...select_many.previously_selected, ...new_selection]);
  const selected = [...selected_union].sort((a,b) => (a-b));

  return selected;
}