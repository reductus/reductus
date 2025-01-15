let template = `
<div class="bool-ui">
  <label>
    {{field.label}}
    <input
      type="checkbox"
      :id="field.id"
      v-model="local_value"
      @change="$emit('change', field.id, local_value)"
    />
  </label>
</div>
`;

export const BoolUi = {
  name: "bool-ui",
  props: ["field", "value"],
  data: function () {
    return {
      local_value: ((this.value == null) ? this.field.default : this.value)
    }
  },
  template
}