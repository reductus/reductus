import { createApp } from 'vue';

let template = /*html*/`
<dialog ref="dialog" class="export-dialog" style="max-width:800px;">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">{{ banner_data.title || 'Welcome' }}</h5>
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
      this.$refs?.dialog?.showModal();
    },
    close() {
      this.$refs?.dialog?.close();
    },
    onClose() {
      this.$emit("close");
    }
  }
};


export const startup_banner_dialog = {};

startup_banner_dialog.create_instance = function() {
  let target  = document.createElement('div');
  document.body.appendChild(target);
  this.instance = createApp(startup_banner_dialog_component).mount(target);
}
