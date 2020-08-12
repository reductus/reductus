let template = `
<div class="fields">
  <label>
    {{field.label}}
    <input
      type="text"
      :id="field.id"
      :placeholder="field.default"
      v-model="value"
      @change="$emit('change', field.id, value)"
    />
  </label>
</div>
`;

export const StrUi = {
  name: "str-ui",
  props: {
    "field": Object, 
    "value": String
  },
  template
}