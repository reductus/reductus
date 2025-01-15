let template = `
<div class="opt-ui">
  <label>
    {{field.label}}
    <select
      :id="field.id"
      :value="value"
      @change="$emit('change', field.id, $event.target.value)"
    >
      <option value="" v-if="value == null"></option>
      <option v-for="(c, i) in field.typeattr.choices" :value="c[1]">{{c[0]}}</option>
    </select>
  </label>
  <span v-if="value == null">
    <em>default: {{field.default}}</em>
  </span>
</div>
`;

export const OptUi = {
  name: "opt-ui",
  props: ["field", "value"],
  template
}