import { extend } from '../../libraries.js';
import { plotter } from '../../plot.js';

let field_template = `
<div class="fields">
  <label>
    {{field.label}}
    <div class="patch-key">
      Key: {{field.typeattr.key}}
    </div>
    <div 
      class="patch" 
      v-for="(patch, index) in (value || [])"
      :key="JSON.stringify(patch)"
      > 
        <button style="color:red;font-weight:bold;" @click="remove(index)">x</button>
        <span class="patch-path" style="color:purple;"><em>{{patch.path}}</em></span>: 
        <span class="patch-value">{{patch.value}}</span>    
    </div>
  </label>
</div>
`;

export const PatchUi = {
  name: 'patch_metadata-ui',
  props: ["field", "value", "add_interactors"],
  computed: {
    local_value: function() { return extend(true, [], this.value) },
    key_col: function() { return this.field.typeattr.key }
  },
  methods: {
    update_patch(row, col, value) {
      let key = row[this.key_col];
      let path = `/${key}/${col}`;
      let local_value = this.local_value;
      let existing = local_value.find(p => (p.path == path));
      if (existing) {
        existing.value = value;
      }
      else {
        local_value.push({op: "replace", path, value});
      }
      this.$emit("change", this.field.id, local_value);
    },
    remove(index) {
      let local_value = this.local_value;
      local_value.splice(index, 1);
      this.$emit("change", this.field.id, local_value);
    }
  },
  template: field_template,
  mounted: function() {
    if (this.add_interactors) {
      let chart = plotter.instance.active_plot;
      chart.editing = true;
      chart.key_col = this.key_col;
      chart.$set(chart, 'patches', this.value || []);
      chart.$on("change", (row, col, value) => {
        this.update_patch(row, col, value);
      })
    }
  },
  updated: function() {
    if (this.add_interactors) {
      let chart = plotter.instance.active_plot;
      chart.$set(chart, 'patches', this.value || []);
    }
  }
}