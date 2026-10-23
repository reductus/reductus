import * as Vue from 'vue';
import { emitter } from '../bus.js';

let template = `
<div class="metadata-table">
  <table class="metadata">
    <thead>
      <tr>
        <th v-for="col in cols" :key="col"><div class="metadata-entry metadata-header">{{headerLabel(col)}}</div></th>
      </tr>
    </thead>
    <tbody>
      <tr 
        ref="rows"
        v-for="row in metadata" 
        :key="JSON.stringify(row)"
        class="metadata-row"
        >
        <td 
          v-for="col in cols" 
          :key="col"
          :style="{backgroundColor: (patched(row, col) == null) ? null : 'yellow'}"
          :class="{patched: patched(row, col) != null}"
          :contenteditable="editing && col != key_col"
          @blur="onInput(row, col, $event.target.innerText)"
          :title="pretty(row[col])"
        ><div class="metadata-entry">{{pretty(patched(row, col) || row[col])}}</div></td>
      </tr>
    </tbody>
  </table>
</div>
`;

const MetadataTable = {
  name: "metadata-table",
  emits: ["change"],
  props: {
    cols: {
      type: Array,
      default: () => []
    },
    metadata: {
      type: Array,
      default: () => []
    }
  },
  data: () => ({
    patches: [],
    patchesByPathNew: {},
    editing: false,
    key_col: "",
    precision: 5
  }),
  computed: {
    rowByKey() {
      return Object.fromEntries(this.metadata.map(row => [row[this.key_col], row]));
    },
    patchesByPath() {
      let result = Object.fromEntries(this.patches.map(p => [p.path, p]));
      return result;
    }
  },
  methods: {
    headerLabel(col) {
      // put each part of a dotted metadata key (e.g. "run.configuration") on its own line
      return String(col).replaceAll('.', '\n');
    },
    pretty(value) {
      if (value && value.toPrecision) {
        return value.toPrecision(this.precision);
      }
      else if (typeof value === "object") {
        return JSON.stringify(value, null, 1); }
      else {
        return String(value);
      }
    },
    onInput(row, col, value) {
      //let key = row[this.key_col];
      let oldVal = this.pretty(row[col]);
      if (value != oldVal) {
        this.$emit("change", row, col, value);
        emitter.emit("metadata_table.change", {row, col, value});
      }
    },
    patched(row, col) {
      let path = `/${row[this.key_col]}/${col}`;
      return (this.patchesByPath[path] || {}).value;
    }
  },
  template
}

export function show_plots_metadata(plotdata, plot_controls, target, old_plot) {
  var metadata = plotdata.values.map(function (v) { return v.values });
  var m0 = metadata[0] || {};

  plot_controls.updateShow(["export_data"]);

  var colset = new Set(Object.keys(m0));
  for (var nm of metadata.slice(1)) {
    for (var c of colset) {
      if (!(c in nm)) {
        colset.delete(c);
      }
    }
  }
  var cols = Array.from(colset);
  while (target.firstChild) {
    // clean out the target
    target.removeChild(target.firstChild);
  }
  target.classList.remove("plot");
  let container = document.createElement("div");
  container.classList.add("metadata-table");
  target.appendChild(container);

  let metadata_table = Vue.createApp(MetadataTable, {
    cols,
    metadata
  }).mount(container);

  return metadata_table
}

