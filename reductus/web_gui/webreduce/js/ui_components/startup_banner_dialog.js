import { Vue } from '../libraries.js';

let template = `
<md-dialog :md-active.sync="active" @md-closed="onClose" class="startup-banner-dialog">
  <md-dialog-title>{{ banner_data.title || 'Welcome' }}</md-dialog-title>
  <md-dialog-content>
    <div v-html="banner_data.message" class="banner-message-content"></div>
  </md-dialog-content>
  <md-dialog-actions>
    <md-button @click="close" class="md-primary">{{ banner_data.button_text || 'OK' }}</md-button>
  </md-dialog-actions>
</md-dialog>
`;

export const startup_banner_dialog_component = {
  name: "startup-banner-dialog",
  data: () => ({
    active: false,
    banner_data: {
      title: '',
      message: '',
      button_text: 'OK'
    }
  }),
  template: template,
  methods: {
    open(banner_data) {
      this.banner_data = banner_data || {
        title: 'Welcome',
        message: 'Welcome to the application',
        button_text: 'OK'
      };
      this.active = true;
    },
    close() {
      this.active = false;
    },
    onClose() {
      this.$emit("close");
    }
  }
};

const Component = Vue.extend(startup_banner_dialog_component);

export const startup_banner_dialog = {};

startup_banner_dialog.create_instance = function() {
  let target  = document.createElement('div');
  document.body.appendChild(target);
  this.instance = new Component({}).$mount(target);
}
