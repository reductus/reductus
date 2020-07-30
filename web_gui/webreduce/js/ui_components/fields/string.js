let template = `
<div class="fields">
  <label>
    {{field.label}}
    <input
      type="text"
      :id="field.id"
      :placeholder="field.default"
      v-model="display_value"
      @change="$emit('change', field.id, local_value)"
    />
  </label>
</div>
`;

export const StringUi = {
  name: "string-ui",
  props: ["field", "value"],
  data: function() {
    return {
      local_value: ((this.value == null) ? this.field.default : this.value)
    }
  },
  template
}