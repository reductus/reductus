let template = `
<div class="opt-ui">
  <label>
    {{field.label}}
    <select
      :id="field.id"
      v-model="local_value"
      @change="$emit('change', field.id, local_value)"
    >
      <option v-for="(c, i) in field.typeattr.choices" :value="c[1]">{{c[0]}}</option>
    </select>
  </label>
</div>
`;

export const OptUi = {
  name: "opt-ui",
  props: ["field", "value"],
  data: function() {
    return {
      local_value: ((this.value == null) ? this.field.default : this.value)
    }
  },
  template
}