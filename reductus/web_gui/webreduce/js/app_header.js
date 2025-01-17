import { Vue } from './libraries.js';

let template = `
<div class="app">
  <md-app>
  <md-app-toolbar class="" style="background-color:yellow;">
    <div class="md-toolbar-row">
      <div class="md-toolbar-section-start md-primary">
        <md-button class="md-icon-button" @click="$emit('toggle-menu')">
          <md-icon class="mdi mdi-menu" title="MENU"></md-icon>
        </md-button>
        <span class="md-title"><img src="img/reductus_logo.svg" style="height:2em;"/>Reductus</span>
        <md-button class="md-primary md-small" href="https://doi.org/10.1107/S1600576718011974">[cite]</md-button>
      </div>
      <div class="md-toolbar-section-end">
        <a href="https://www.nist.gov/ncnr" target="_blank">
          <img src="img/NCNR_nonlogo.png" alt="NCNR logo" title="NIST Center for Neutron Research" style="height:2em;padding-right:1.5em;">
        </a>
        <a href="https://www.nist.gov" target="_blank">
              <img src="img/nist-logo.svg" alt="NIST logo" title="National Institute of Standards and Technology" style="height:2em;">
        </a>
      </div>
    </div>  
  </md-app-toolbar>
  </md-app>

  <md-dialog :md-active.sync="api_error.visible">
    <md-dialog-title>API Error</md-dialog-title>
    <pre>{{api_error.message}}</pre>
  </md-dialog>

  <md-dialog 
    :md-click-outside-to-close="false"
    :md-close-on-esc="false"
    :md-active.sync="calculation_progress.visible">
    <md-dialog-title>Processing Calculations</md-dialog-title>
    <md-dialog-content>
      <md-progress-bar 
        md-mode="determinate" 
        class="md-primary"
        :md-value="percent_done">
      </md-progress-bar>
      <span>{{calculation_progress.done}} of {{calculation_progress.total}}</span>
    </md-dialog-content>
    <md-dialog-actions>
      <md-button class="md-accent" @click="$emit('cancel-calculation')">cancel</md-button>
    </md-dialog-actions>
  </md-dialog>

  <md-dialog 
    :md-click-outside-to-close="false"
    :md-close-on-esc="false"
    :md-active.sync="init_progress.visible">
    <md-dialog-title>Initializing</md-dialog-title>
    <md-dialog-content>
      <pre>{{init_progress.status_text}}</pre>
      <md-progress-spinner md-mode="indeterminate"></md-progress-spinner>
    </md-dialog-content>
  </md-dialog>

  <md-snackbar :md-active.sync="snackbar.visible" md-position="center" :md-duration="snackbar.duration">
    <span>{{snackbar.message}}</span>
  </md-snackbar>

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
    }
  },
  template
}

app_header.create_instance = function(target_id) {
  let target = document.getElementById(target_id);
  const HeaderClass = Vue.extend(header);
  this.instance = new HeaderClass({}).$mount(target);
}