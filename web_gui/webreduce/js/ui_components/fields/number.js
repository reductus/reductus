let template = `
<div class="fields">
  <label>
    {{field.label}}
    <input
      :type="(field.multiple) ? 'text' : 'number'"
      :id="field.id"
      :placeholder="field.default"
      :value="display_value"
      @change="display_value = $event.target.value"
    />
  </label>
</div>
`;

export const IntUi = {
  name: "int-ui",
  props: ["field", "value"],
  methods: {
    coerce(value) {
      return 0 | value;
    }
  },
  computed: {
    display_value: {
      get() {
        let v = (this.value != null) ? this.value : this.field.default;
        if (this.multiple) {
          return JSON.stringify(extend(true, [], v))
            .replace(/^\[/, '')
            .replace(/\]$/, '');
        }
        else {
          return v
        }
      },
      set(newValue) {
        let v = (this.multiple) ? JSON.parse('[' + newValue + ']').map(this.coerce) : this.coerce(newValue);
        this.$emit("change", this.field.id, v);
      }
    }
  },
  template
}

const FloatUi = Object.assign({}, IntUi);
FloatUi.name = "float-ui";
FloatUi.methods.coerce = function (value) { return +value }
export { FloatUi }