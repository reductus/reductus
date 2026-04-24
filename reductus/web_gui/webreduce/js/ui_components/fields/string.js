let template = `
<div class="fields">
  <label>
    {{field.label}}
    <input
      type="text"
      :id="field.id"
      :placeholder="placeholder"
      :value="display_value"
      @change="display_value = $event.target.value"
    />
  </label>
</div>
`;

export const StrUi = {
  name: "str-ui",
  props: ["field", "value", "num_datasets_in"],
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
    placeholder() {
      if (this.defaultOuterValue != null) {
        if (this.isMultiple) {
          return JSON.stringify(this.defaultOuterValue);
        }
        else {
          return this.defaultOuterValue;
        }
      }
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
          cv = (this.field.multiple || this.field.length != 1) ? JSON.parse(newValue) : newValue;
        }
        this.$emit("change", this.field.id, cv);
      }
    }
  },
  template
}