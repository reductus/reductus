import { extend } from 'vue';

let template = `
<dialog ref="dialog" class="export-dialog">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">{{ banner_data.title || 'Welcome' }}</h5>
        <button type="button" class="btn-close" @click="close"></button>
      </div>
      <div class="modal-body">
        <div v-html="banner_data.message" class="banner-message-content"></div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-primary" @click="close">{{ banner_data.button_text || 'OK' }}</button>
      </div>
    </div>
  </div>
</dialog>
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

const Component = extend(startup_banner_dialog_component);

export const startup_banner_dialog = {};

startup_banner_dialog.create_instance = function() {
  let target  = document.createElement('div');
  document.body.appendChild(target);
  this.instance = new Component({}).$mount(target);
}
