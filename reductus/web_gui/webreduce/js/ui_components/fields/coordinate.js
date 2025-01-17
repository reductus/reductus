let template = `
<div class="coordinate-ui">
  <label>
    {{field.label}}
    <div v-for="(axis, index) in axes">
      <label>
        {{axis}}
        <input
          type="number"
          v-model="local_value[index]"
          :placeholder="(field.default || [])[index]"
          @change="$emit('change', field.id, local_value)"
        />
      </label>
    </div>
  </label>
</div>
`;

export const CoordinateUi = {
  name: "coordinate-ui",
  props: ["field", "value"],
  data: function () {
    return {
      local_value: ((this.value == null) ? this.field.default : this.value),
      axes: ["x", "y"]
    }
  },
  template
}