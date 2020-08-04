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
      v-for="(patch, index) in local_value"
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
  data: function() {
    return {
      local_value: extend(true, [], this.value),
      key_col: this.field.typeattr.key
    }
  },
  methods: {
    update_patch(row, col, value) {
      let key = row[this.key_col];
      let path = `/${key}/${col}`;
      let existing = this.local_value.find(p => (p.path == path));
      if (existing) {
        existing.value = value;
      }
      else {
        this.local_value.push({op: "replace", path, value});
      }
      this.$emit("change", this.field.id, this.local_value);
    },
    remove(index) {
      this.$delete(this.local_value, index);
      this.$emit("change", this.field.id, this.local_value);
    }
  },
  template: field_template,
  mounted: function() {
    if (this.add_interactors) {
      let chart = plotter.instance.active_plot;
      chart.editing = true;
      chart.key_col = this.field.typeattr.key;
      chart.$set(chart, 'patches', this.local_value);
      chart.$on("change", (row, col, value) => {
        this.update_patch(row, col, value);
      })
    }
  }
}