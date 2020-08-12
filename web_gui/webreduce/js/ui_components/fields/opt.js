let template = `
<div class="opt-ui">
  <label>
    {{field.label}}
    <select
      :id="field.id"
      :value="(value != null) ? value : field.default"
      @change="$emit('change', field.id, $event.target.value)"
    >
      <option v-for="(c, i) in field.typeattr.choices" :value="c[1]">{{c[0]}}</option>
    </select>
  </label>
</div>
`;

export const OptUi = {
  name: "opt-ui",
  props: ["field", "value"],
  template
}