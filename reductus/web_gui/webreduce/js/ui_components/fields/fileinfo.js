let template = `
<div class="fileinfo-field">
  <div class="fields">
    <input @change="$emit('activate')" type="radio" name="fileinfo" :id="field.id" :checked="active" />
    <label :for="field.id" >
      <span class="fileinfo-label">{{field.id + '(' + (value || []).length + ')'}}</span>
    </label>
  </div>
</div>
`;

export const FileinfoUi = {
  name: 'fileinfo-ui',
  props: ["field", "value", "active"],
  mounted: function() {
    // this should be called every time a module is clicked on that has fileinfo, 
    // creating a new fields element.
    if (this.active) {
      this.$emit("activate")
    }
  },
  template
}