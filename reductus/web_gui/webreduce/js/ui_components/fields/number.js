import { extend } from '../../libraries.js';

let template = `
<div class="fields">
  <label>
    {{field.label}}
    <input
      :type="(isMultiple) ? 'text' : 'number'"
      :style="(isMultiple) ? '' : 'width:10em;'"
      :id="field.id"
      :placeholder="(defaultOuterValue == null) ? '' : JSON.stringify(defaultOuterValue)"
      :value="display_value"
      @change="display_value = $event.target.value"
    />
  </label>
</div>
`;

export const IntUi = {
  name: "int-ui",
  props: ["field", "value", "num_datasets_in"],
  methods: {
    coerceAll(value) {
      if (Array.isArray(value)) {
        return value.map(x => (this.coerceAll(x)));
      }
      else {
        return this.coerceType(value)
      }
    },
    coerceType(value) {
      return 0 | value;
    }
  },
  computed: {
    isMultiple() {
      return (this.field.multiple || this.field.length != 1)
    },
    defaultInnerValue() {
      let d = this.field.default;
      if (this.field.length > 1) { return Array.from(new Array(this.field.length)).map(x => d) }
      else { return d }
    },
    defaultOuterValue() {
      if (this.field.length == 0) {
        return Array.from(new Array(this.num_datasets_in)).map(x => this.defaultInnerValue);
      }
      else { return this.defaultInnerValue }
    },
    display_value: {
      get() {
        if (this.value == null) {
          return ""
        }
        else {
          let v = this.value;
          return (this.field.multiple || this.field.length != 1) ? JSON.stringify(v) : v;
        }
      },
      set(newValue) {
        let cv;
        if (newValue == "") {
          cv = null
        }
        else {
          let v = (this.field.multiple || this.field.length != 1) ? JSON.parse(newValue) : newValue;
          cv = this.coerceAll(v);
        }
        this.$emit("change", this.field.id, cv);
      }
    }
  },
  template
}

const FloatUi = extend(true, {}, IntUi);
FloatUi.name = "float-ui";
FloatUi.methods.coerceType = function (value) { return +value }
export { FloatUi }