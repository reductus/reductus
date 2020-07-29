import { extend } from '../../libraries.js';

let template = `
<div class="fields">
  <label>
    {{field.label}}
    <textarea
      :id="field.id"
      :placeholder="field.default"
      :rows="local_value.length"
      v-model="display_value"
      @change="$emit('change', field.id, local_value)"
    ></textarea>
  </label>
</div>
`;

export const ScaleUi = {
  name: "scale-ui",
  props: ["field", "value"],
  data: function () {
    let local_value;
    if (this.value != null) {
      local_value = extend(true, [], this.value);
    }
    else {
      local_value = extend(true, [], this.field.default);
    }
    return { local_value }
  },
  computed: {
    display_value: {
      get() {
        return JSON.stringify(this.local_value, null, 2)
          .replace(/^\[\s+/, '')
          .replace(/\s+\]$/, '');
      },
      set(newValue) {
        this.local_value = JSON.parse('[' + newValue + ']').map(x => (+x));
      }
    }
  },
  mounted: function () {
    // create the interactor here.
  },
  template
}