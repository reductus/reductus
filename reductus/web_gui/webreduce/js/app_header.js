const template = `
<div class="app">
  <nav class="navbar" style="background-color: yellow;">
    <div class="container-fluid">
      <div class="d-flex align-items-center">
        <button class="btn btn-link" @click="emitter.emit('toggle-menu', { show: true })" style="padding: 0; margin-right: 1rem;">
          <i class="mdi mdi-menu" title="MENU" style="font-size: 1.5em;"></i>
        </button>
        <span style="font-weight: bold; font-size: 1.25em;">
          <img src="img/reductus_logo.svg" style="height: 2em; vertical-align: middle; margin-right: 0.5em;"/>Reductus
        </span>
        <a href="https://doi.org/10.1107/S1600576718011974" class="btn btn-sm btn-link">[cite]</a>
      </div>
      <div>
        <a href="https://www.nist.gov/ncnr" target="_blank">
          <img src="img/NCNR_nonlogo.png" alt="NCNR logo" title="NIST Center for Neutron Research" style="height: 2em; padding-right: 1.5em;">
        </a>
        <a href="https://www.nist.gov" target="_blank">
          <img src="img/nist-logo.svg" alt="NIST logo" title="National Institute of Standards and Technology" style="height: 2em;">
        </a>
      </div>
    </div>
  </nav>

  <dialog ref="api_error_dialog" class="api-error-dialog" style="width: 600px;">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">API Error</h5>
          <button type="button" class="btn-close" @click="close_api_error"></button>
        </div>
        <div class="modal-body">
          <pre style="max-height: 400px; overflow-y: auto;">{{api_error.message}}</pre>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="close_api_error">Close</button>
        </div>
      </div>
    </div>
  </dialog>

  <dialog ref="calculation_progress_dialog" class="calculation-progress-dialog" style="width: 400px;">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Processing Calculations</h5>
        </div>
        <div class="modal-body">
          <div class="progress mb-3" style="height: 25px;">
            <div class="progress-bar" :style="{ width: percent_done + '%' }">
              {{ percent_done.toFixed(0) }}%
            </div>
          </div>
          <p>{{calculation_progress.done}} of {{calculation_progress.total}}</p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-danger" @click="emitter.emit('app_header.cancel_calculation')">Cancel</button>
        </div>
      </div>
    </div>
  </dialog>

  <dialog ref="init_progress_dialog" class="init-progress-dialog" style="width: 400px;">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Initializing</h5>
        </div>
        <div class="modal-body">
          <pre style="max-height: 200px; overflow-y: auto;">{{init_progress.status_text}}</pre>
          <div class="spinner-border" role="status" style="margin-top: 1rem;">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
      </div>
    </div>
  </dialog>

  <div class="snackbar" v-if="snackbar.visible" style="position: fixed; bottom: 1rem; left: 50%; transform: translateX(-50%); z-index: 9999; min-width: 300px;">
    <div class="alert alert-info" role="alert">
      {{snackbar.message}}
    </div>
  </div>

</div>
`;

export const app_header = {};

export const headerComponent = {
  name: 'reductus-header',
  props: {
    emitter: Object
  },
  data: () => ({
    api_error: {
      message: ""
    },
    init_progress: {
      status_text: "Loading pyodide backend..."
    },
    calculation_progress: {
      done: 0,
      total: 1
    },
    snackbar: {
      message: "",
      duration: 4000,
      timeout_id: null,
      visible: false
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
      this.$nextTick(() => {
        if (this.$refs.api_error_dialog) {
          this.$refs.api_error_dialog.showModal();
        }
      });
    },
    close_api_error() {
      if (this.$refs.api_error_dialog) {
        this.$refs.api_error_dialog.close();
      }
    },
    async show_calculation_progress(total) {
      this.calculation_progress.total = total;
      this.calculation_progress.done = 0;
      this.$nextTick(() => {
        if (this.$refs.calculation_progress_dialog) {
          this.$refs.calculation_progress_dialog.showModal();
        }
      });
    },
    close_calculation_progress() {
      if (this.$refs.calculation_progress_dialog) {
        this.$refs.calculation_progress_dialog.close();
      }
    },
    show_init_progress(status_text = "Loading pyodide backend...") {
      this.init_progress.status_text = status_text;
      this.$nextTick(() => {
        if (this.$refs.init_progress_dialog) {
          this.$refs.init_progress_dialog.showModal();
        }
      });
    },
    close_init_progress() {
      // Ensure the dialog is fully rendered before closing
      this.$nextTick(() => {
        if (this.$refs.init_progress_dialog) {
          this.$refs.init_progress_dialog.close();
        }
      });
    },
    show_snackbar(message, duration=4000) {
      if (this.snackbar.timeout_id) {
        clearTimeout(this.snackbar.timeout_id);
      }
      this.snackbar.message = message;
      this.snackbar.duration = duration;
      this.snackbar.visible = true;
      if (duration > 0) {
        this.snackbar.timeout_id = setTimeout(() => {
          this.snackbar.visible = false;
        }, duration);
      }
    },
    hide_snackbar() {
      if (this.snackbar.timeout_id) {
        clearTimeout(this.snackbar.timeout_id);
      }
      this.snackbar.visible = false;
    }
  },
  mounted() {
    // Ensure all dialogs are closed on initial load
    this.$nextTick(() => {
      if (this.$refs.api_error_dialog) {
        this.$refs.api_error_dialog.close();
      }
      if (this.$refs.calculation_progress_dialog) {
        this.$refs.calculation_progress_dialog.close();
      }
      if (this.$refs.init_progress_dialog) {
        this.$refs.init_progress_dialog.close();
      }
    });
  },
  template
}
