import * as Vue from 'vue';

let template = `
<dialog ref="dialog" class="export-dialog" style="width: 500px;">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Export Data</h5>
        <button type="button" class="btn-close" @click="close"></button>
      </div>
      
      <div class="modal-body">
        <!-- Step Indicator -->
        <div class="mb-3">
          <div class="progress" style="height: 2px;">
            <div 
              class="progress-bar" 
              :style="{ width: stepProgress + '%' }">
            </div>
          </div>
          <div class="mt-2 small text-muted">
            Step {{ stepNumber }} of 3: {{ stepTitle }}
          </div>
        </div>

        <!-- Step 1: Select Export Type -->
        <div v-show="active_step === 'select_export_type'" class="step-content">
          <h6>Select Export Type</h6>
          <div class="mb-3 d-flex gap-3">
            <div v-for="(export_type, index) in export_types" class="form-check">
              <input 
                type="radio" 
                :id="'export_type_' + index"
                class="form-check-input" 
                v-model.number="selected_export_type" 
                :value="index"
              />
              <label class="form-check-label" :for="'export_type_' + index">
                {{export_type}}
              </label>
            </div>
          </div>
          
          <hr/>
          
          <div class="form-check mb-3">
            <input 
              type="checkbox" 
              id="combine_outputs"
              class="form-check-input" 
              v-model="combine_outputs"
            />
            <label class="form-check-label" for="combine_outputs">
              Combine Outputs
            </label>
          </div>
          
          <hr/>
          
          <div class="d-flex gap-2 justify-content-end">
            <button 
              type="button" 
              class="btn btn-primary"
              :disabled="selected_export_type===null" 
              @click="onExportSelect">
              Continue
            </button>
            <button type="button" class="btn btn-secondary" @click="close">Cancel</button>
          </div>
        </div>

        <!-- Step 2: Retrieve From Server -->
        <div v-show="active_step === 'retrieve'" class="step-content">
          <h6>Retrieve From Server</h6>
          <div class="progress">
            <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>
          </div>
        </div>

        <!-- Step 3: Route Exported Data -->
        <div v-show="active_step === 'select_destination'" class="step-content">
          <h6>Route Exported Data</h6>
          
          <div class="mb-3">
            <label for="filename" class="form-label">Filename:</label>
            <input 
              type="text" 
              id="filename"
              class="form-control" 
              v-model="filename"
              placeholder="Enter filename"
            />
          </div>
          
          <div class="mb-3">
            <label class="form-label">Export Target:</label>
            <div v-for="(export_target, index) in export_targets" class="form-check">
              <input 
                type="radio" 
                :id="'export_target_' + index"
                class="form-check-input" 
                v-model.number="selected_export_target" 
                :value="index"
              />
              <label class="form-check-label" :for="'export_target_' + index">
                {{export_target.label}}
              </label>
            </div>
          </div>
          
          <hr/>
          
          <div class="d-flex gap-2 justify-content-end">
            <button type="button" class="btn btn-primary" @click="onExportRoute">Export</button>
            <button type="button" class="btn btn-secondary" @click="close">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>
`;

export const exportDialog = {
  name: "export-dialog",
  props: ["emitter"],
  data() {
    return {
      selected_export_type: 0,
      export_types: [],
      combine_outputs: true,
      active_step: "select_export_type",
      export_select_done: false,
      retrieve_done: false,
      export_targets: [],
      selected_export_target: 0,
      filename: ""
    };
  },
  computed: {
    stepNumber() {
      const steps = ["select_export_type", "retrieve", "select_destination"];
      return steps.indexOf(this.active_step) + 1;
    },
    stepTitle() {
      const titles = {
        select_export_type: "Select Export Type",
        retrieve: "Retrieve From Server",
        select_destination: "Route Exported Data"
      };
      return titles[this.active_step] || "";
    },
    stepProgress() {
      const steps = ["select_export_type", "retrieve", "select_destination"];
      const index = steps.indexOf(this.active_step);
      return ((index + 1) / steps.length) * 100;
    }
  },
  methods: {
    open(export_types=[]) {
      this.export_types = export_types;
      this.active_step = "select_export_type";
      this.retrieve_done = false;
      this.export_select_done = false;
      this.selected_export_type = 0; // default to first export type
      this.$nextTick(() => {
        this.$refs.dialog.showModal();
      });
    },
    close() {
      this.$refs.dialog.close();      
    },
    onExportSelect() {
      const payload = {
        export_type: this.export_types[this.selected_export_type],
        combine_outputs: this.combine_outputs
      }
      this.emitter.emit('export-select', payload);
      this.active_step = "retrieve";
      this.export_select_done = true;
    },
    retrieved(suggested_name) {
      // callback that is fired by external controller (editor) when data is ready
      this.filename = suggested_name;
      this.active_step = "select_destination";
      this.retrieve_done = true;
    },
    onExportRoute() {
      const payload = {
        export_target: this.export_targets[this.selected_export_target],
        filename: this.filename
      }
      this.emitter.emit('export-route', payload);
      this.close();
    }
  },
  beforeUnmount() {
    if (this.$el && this.$el.parentNode) {
      this.$el.parentNode.removeChild(this.$el);
    }
  },
  template
}

export const export_dialog = {};

export_dialog.create_instance = function(emitter) {
  let target  = document.createElement('div');
  document.body.appendChild(target);
  this.instance = Vue.createApp(exportDialog, { emitter }).mount(target);
}