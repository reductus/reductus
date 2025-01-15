import { Vue } from '../libraries.js';

let template = `
<div class="metadata-table">
  <table class="metadata">
    <thead>
      <tr>
        <th v-for="col in cols" :key="col">{{col}}</th>
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
        >{{pretty(patched(row, col) || row[col])}}</td>
      </tr>
    </tbody>
  </table>
</div>
`;

const MetadataTable = {
  name: "metadata-table",
  data: () => ({
    cols: [],
    metadata: [],
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
      console.log(JSON.stringify(result));
      return result;
    }
  },
  methods: {
    pretty(value) {
      if (value && value.toPrecision) {
        return value.toPrecision(this.precision);
      }
      else {
        return value;
      }
    },
    onInput(row, col, value) {
      //let key = row[this.key_col];
      let oldVal = this.pretty(row[col]);
      if (value != oldVal) {
        this.$emit("change", row, col, value);
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
  container.style.overflowX = "scroll";
  target.appendChild(container);

  let MetadataTableClass = Vue.extend(MetadataTable);
  let metadata_table = new MetadataTableClass({
    data: () => ({
      cols,
      metadata
    }),
    mounted: function () {
      console.log(this.metadata, this.$refs.rows);
      // reset patches?
      //this.patched = [];
    }
  }).$mount(container);

  return metadata_table
}

