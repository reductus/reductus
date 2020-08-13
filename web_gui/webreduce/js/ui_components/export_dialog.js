import { Vue } from '../libraries.js';

let template = `
<md-dialog :md-active.sync="active" @md-closed="onClose">
  <md-dialog-title>Export Data</md-dialog-title>
  <md-dialog-content>
    <md-steppers :md-active-step.sync="active_step" md-linear>
      <md-step id="select_export_type" md-label="Select Export Type" :md-done.sync="export_select_done" :md-editable="false">

        <template v-for="(export_type, index) in export_types">
          <md-radio v-model="selected_export_type" :value="index">
            {{export_type}}
          </md-radio>
        </template>
        <md-divider/>
        <md-checkbox v-model="combine_outputs" >Combine Outputs</md-checkbox>
        <md-divider/>
        <md-button :disabled="selected_export_type==null" @click="onExportSelect">continue</md-button>
        <md-button class="md-raised md-accent" @click="close">cancel</md-button>
      </md-step>
      <md-step id="retrieve" :md-done.sync="retrieve_done" md-label="Retrieve From Server" :md-editable="false">
        <md-progress-bar md-mode="indeterminate"></md-progress-bar>
      </md-step>
      <md-step id="select_destination" md-label="Route Exported Data">
        <md-field>
          <label>Filename:</label>
          <md-input v-model="filename"></md-input>
        </md-field>
        <template v-for="(export_target, index) in export_targets">
          <md-radio v-model="selected_export_target" :value="index">
            {{export_target.label}}
          </md-radio>
        </template>
        <md-divider/>
        <md-button class="md-raised md-primary" @click="onExportRoute">export</md-button>
        <md-button class="md-raised md-accent" @click="close">cancel</md-button>
      </md-step>
    </md-steppers>
  </md-dialog-content>
</md-dialog>
`;

export const exportDialog = {
  name: "export-dialog",
  data: () => ({
    active: false,
    selected_export_type: 0,
    export_types: [],
    combine_outputs: true,
    active_step: "select_export_type",
    export_select_done: false,
    retrieve_done: false,
    export_targets: [],
    selected_export_target: 0,
    filename: ""
  }),
  methods: {
    open(export_types=[]) {
      this.export_types = export_types;
      this.active_step = "select_export_type";
      this.retrieve_done = false;
      this.export_select_done = false;
      this.active = true;
    },
    close() {
      this.active = false;      
    },
    onClose() {
      this.$off("export-select");
      this.$off("export-route");
    },
    onExportSelect() {
      this.$emit('export-select', this.export_types[this.selected_export_type], this.combine_outputs);
      this.active_step = "retrieve"
      this.export_select_done = true;
    },
    retrieved(suggested_name) {
      // callback that is fired by external controller (editor) when data is ready
      this.filename = suggested_name;
      this.active_step = "select_destination";
      this.retrieve_done = true;
    },
    onExportRoute() {
      this.$emit('export-route', this.filename, this.export_targets[this.selected_export_target]);
      this.active = false;
    }
  },
  beforeDestroy() {
    this.$el.parentNode.removeChild(this.$el);
  },
  template
}

const ExportDialogComponent = Vue.extend(exportDialog);

export const export_dialog = {};

export_dialog.create_instance = function() {
  let target  = document.createElement('div');
  document.body.appendChild(target);
  this.instance = new ExportDialogComponent({}).$mount(target);
}