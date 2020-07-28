let template = `
<div class="fields">
  <label>
    {{field.label}}
    <input
      :type="(field.multiple) ? 'text' : 'number'"
      :id="field.id"
      :placeholder="field.default"
      v-model="display_value"
      @change="$emit('change', field.id, local_value)"
    />
  </label>
</div>
`;

export const IntUi = {
  name: "int-ui",
  props: ["field", "value"],
  data: function() {
    return {
      local_value: ((this.value == null) ? this.field.default : this.value)
    }
  },
  computed: {
    display_value: {
      get() {
        if (this.multiple) {
          return JSON.stringify(this.local_value)
            .replace(/^\[/, '')
            .replace(/\]$/, '');
        }
        else {
          return this.local_value
        }
      },
      set(newValue) {
        if (this.multiple) {
          this.local_value = JSON.parse('[' + newValue + ']').map(x => (0 | x));
        }
        else {
          // this is a js trick to cast to int
          this.local_value = (0 | newValue);
        }
      }
    }
  },
  template
}

export const FloatUi = {
  name: "float-ui",
  props: ["field", "value"],
  data: function() {
    return {
      local_value: ((this.value == null) ? this.field.default : this.value)
    }
  },
  computed: {
    display_value: {
      get() {
        if (this.multiple) {
          return JSON.stringify(this.local_value)
            .replace(/^\[/, '')
            .replace(/\]$/, '');
        }
        else {
          return this.local_value
        }
      },
      set(newValue) {
        if (this.multiple) {
          this.local_value = JSON.parse('[' + newValue + ']').map(x => (+x));
        }
        else {
          // this is a js trick to cast to float
          this.local_value = +newValue;
        }
      }
    }
  },
  template
}