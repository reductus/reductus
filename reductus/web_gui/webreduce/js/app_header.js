import { Vue } from './libraries.js';

let template = `
<div>
  <dialog ref="apiErrorDialog" class="modal-dialog modal-lg">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">API Error</h5>
        <button type="button" class="btn-close" @click="api_error.visible = false"></button>
      </div>
      <div class="modal-body">
        <pre>{{api_error.message}}</pre>
      </div>
    </div>
  </dialog>

  <dialog ref="calculationDialog" class="modal-dialog modal-lg">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Processing Calculations</h5>
      </div>
      <div class="modal-body">
        <div class="progress mb-2">
          <div class="progress-bar progress-bar-striped bg-primary" role="progressbar" :style="{width: percent_done + '%'}" :aria-valuenow="percent_done" aria-valuemin="0" aria-valuemax="100"></div>
        </div>
        <span>{{calculation_progress.done}} of {{calculation_progress.total}}</span>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-danger" @click="$emit('cancel-calculation')">Cancel</button>
      </div>
    </div>
  </dialog>

  <dialog ref="initDialog" class="modal-dialog modal-lg">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Initializing</h5>
      </div>
      <div class="modal-body">
        <pre>{{init_progress.status_text}}</pre>
        <div class="d-flex justify-content-center align-items-center" style="height:40px;">
          <span class="spinner-border text-primary" role="status" aria-hidden="true"></span>
        </div>
      </div>
    </div>
  </dialog>

  <div class="toast-container position-fixed top-0 end-0 p-3" style="z-index: 1080;">
    <div class="toast align-items-center text-bg-dark border-0"
         :class="{show: snackbar.visible, hide: !snackbar.visible}"
         role="alert" aria-live="assertive" aria-atomic="true"
         style="transition: opacity 0.5s; opacity: 0;"
         :style="snackbar.visible ? 'opacity:1;' : 'opacity:0;'">
      <div class="d-flex">
        <div class="toast-body">
          {{snackbar.message}}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" @click="snackbar.visible = false" aria-label="Close"></button>
      </div>
    </div>
  </div>

</div>
`;

export const app_header = {};

const header = {
  name: 'reductus-header',
  data: () => ({
    api_error: {
      visible: false,
      message: ""
    },
    init_progress: {
      visible: true,
      status_text: "Loading pyodide backend..."
    },
    calculation_progress: {
      visible: false,
      done: 0,
      total: 1
    },
    snackbar: {
      visible: false,
      duration: 4000,
      message: ""
    }
  }),
  computed: {
    percent_done() {
      return 100.0 * this.calculation_progress.done / (this.calculation_progress.total || 1);
    }
  },
  methods: {
    show_api_error(message) {
      this.api_error.message = message;
      this.api_error.visible = true;
    },
    async show_calculation_progress(total) {
      this.$off("cancel-calculation");
      this.calculation_progress.total = total;
      this.calculation_progress.done = 0;
      this.calculation_progress.visible = true;
    },
    show_snackbar(message, duration=4000) {
      this.snackbar.message = message;
      this.snackbar.duration = duration;
      this.snackbar.visible = true;
      if (this._snackbarTimeout) clearTimeout(this._snackbarTimeout);
      this._snackbarTimeout = setTimeout(() => {
        this.snackbar.visible = false;
      }, duration);
    }
  },
  template,
  watch: {
    'api_error.visible': function(val) {
      const dlg = this.$refs.apiErrorDialog;
      if (!dlg) return;
      if (val) {
        if (dlg.open !== true) dlg.showModal();
      } else {
        if (dlg.open) dlg.close();
      }
    },
    'calculation_progress.visible': function(val) {
      const dlg = this.$refs.calculationDialog;
      if (!dlg) return;
      if (val) {
        if (dlg.open !== true) dlg.showModal();
      } else {
        if (dlg.open) dlg.close();
      }
    },
    'init_progress.visible': function(val) {
      const dlg = this.$refs.initDialog;
      if (!dlg) return;
      if (val) {
        if (dlg.open !== true) dlg.showModal();
      } else {
        if (dlg.open) dlg.close();
      }
    }
  }
}

app_header.create_instance = function(target_id) {
  let target = document.getElementById(target_id);
  const HeaderClass = Vue.extend(header);
  this.instance = new HeaderClass({}).$mount(target);
}