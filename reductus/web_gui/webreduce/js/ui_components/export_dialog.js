import { Vue } from '../libraries.js';

let template = `
<dialog v-if="active" open class="modal-dialog modal-lg" style="max-width:600px;">
  <div class="modal-content">
    <div class="modal-header">
      <h5 class="modal-title">Export Data</h5>
      <button type="button" class="btn-close" @click="close"></button>
    </div>
    <div class="modal-body">
      <!-- Step 1: Select Export Type -->
      <div v-if="active_step === 'select_export_type'">
        <div class="mb-3"><strong>Select Export Type</strong></div>
        <div class="form-check" v-for="(export_type, index) in export_types" :key="index">
          <input class="form-check-input" type="radio" :id="'export_type_' + index" v-model="selected_export_type" :value="index">
          <label class="form-check-label" :for="'export_type_' + index">{{export_type}}</label>
        </div>
        <div class="form-check mt-3">
          <input class="form-check-input" type="checkbox" id="combine_outputs" v-model="combine_outputs">
          <label class="form-check-label" for="combine_outputs">Combine Outputs</label>
        </div>
        <div class="mt-4 d-flex gap-2">
          <button class="btn btn-primary" :disabled="selected_export_type==null" @click="onExportSelect">Continue</button>
          <button class="btn btn-secondary" @click="close">Cancel</button>
        </div>
      </div>
      <!-- Step 2: Retrieve From Server -->
      <div v-if="active_step === 'retrieve'">
        <div class="mb-3"><strong>Retrieve From Server</strong></div>
        <div class="progress">
          <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>
        </div>
      </div>
      <!-- Step 3: Route Exported Data -->
      <div v-if="active_step === 'select_destination'">
        <div class="mb-3"><strong>Route Exported Data</strong></div>
        <div class="mb-3">
          <label for="filename" class="form-label">Filename:</label>
          <input type="text" class="form-control" id="filename" v-model="filename">
        </div>
        <div class="form-check" v-for="(export_target, index) in export_targets" :key="index">
          <input class="form-check-input" type="radio" :id="'export_target_' + index" v-model="selected_export_target" :value="index">
          <label class="form-check-label" :for="'export_target_' + index">{{export_target.label}}</label>
        </div>
        <div class="mt-4 d-flex gap-2">
          <button class="btn btn-primary" @click="onExportRoute">Export</button>
          <button class="btn btn-secondary" @click="close">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</dialog>
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