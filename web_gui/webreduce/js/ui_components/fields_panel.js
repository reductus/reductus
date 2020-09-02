import { Vue, extend } from '../libraries.js';
import { Components } from './fields/components.js';

let template = `
<div class="fields-panel">
  <div class="hideable" v-show="visible">
    <h3>{{ module_def.name }}</h3>
    <button @click="help">help</button>
    <fileinfo-ui 
      v-for="(field, index) in fileinfos"
      :key="base_key + field.id"
      ref="fileinfos"
      :active="active_fileinfo == index"
      :field="field"
      :value="local_config[field.id]"
      @activate="activate_fileinfo(index)"
      >

    </fileinfo-ui>
    <div 
      v-for="(field, index) in fields"
      :class="['fields', field.datatype]"
      oldkey="JSON.stringify(field)+(module.config || {})[field.id]"
      :key="base_key + field.id"
      ref="fields"
      >
      <component 
        v-bind:is="field.datatype + '-ui'"
        :field="field"
        :value="local_config[field.id]"
        :num_datasets_in="num_datasets_in"
        :add_interactors="add_interactors"
        class="item-component"
        @change="changed">
      </component>
    </div>
    <div class="control-buttons" style="position:absolute;bottom:10px;">
      <button class="accept config" @click="accept_clicked">{{(auto_accept.value) ? "replot" : "accept"}}</button>
      <button class="clear config" @click="clear">clear</button>
    </div>
  </div>
</div>
`

export const FieldsPanel = {
  name: "fields-panel",
  components: Components,
  data: () => ({
    visible: true,
    timestamp: 0, // last clicked
    module: {},
    local_config: {},
    num_datasets_in: 0,
    module_def: {},
    module_id: null,
    terminal_id: null,
    auto_accept: { value: true },
    active_fileinfo: 0
  }),
  computed: {
    fileinfos() {
      return (this.module_def.fields || []).filter(f => (f.datatype == 'fileinfo'));
    },
    fields() {
      return (this.module_def.fields || []).filter(f => (f.datatype != 'fileinfo'));
    },
    add_interactors() {
      return (this.terminal_id != null && this.terminal_id == (this.module_def.inputs[0] || {}).id);
    },
    base_key() {
      return `${this.module_id}:${this.terminal_id}:${this.timestamp}:`;
    }
  },
  methods: {
    reset_local_config() {
      // this.fields.forEach((f) => {
      //   let id = f.id;
      //   if (this.module.config && id in this.module.config) {
      //     if (Array.isArray(this.local_config[id]) && Array.isArray(this.module.config[id])) {
      //       this.local_config[id].splice(0, this.local_config[id].length, ...this.module.config[id]);
      //     }
      //     else {
      //       this.$set(this.local_config, id, this.module.config[id]);
      //     }
      //   }
      //   else {
      //     this.$delete(this.local_config, id);
      //   }
      // })
      this.local_config = extend(true, {}, this.module.config);
    },
    help() {
      let helpwindow = window.open("", "help", "location=0,toolbar=no,menubar=no,scrollbars=yes,resizable=yes,width=960,height=480");
      helpwindow.document.title = "Web reduction help";
      helpwindow.document.write(this.module_def.description);
      helpwindow.document.close();
      if (helpwindow.MathJax) {
        helpwindow.MathJax.Hub.Queue(["Typeset", helpwindow.MathJax.Hub]);
      }
    },
    changed(id, value) {
      if (this.auto_accept.value) {
        this.accept_change(id, value);
      }
      else {
        if (value == null) {
          this.$delete(this.local_config, id);
        }
        else {
          this.$set(this.local_config, id, value);
        }
      }
    },
    accept_change(id, value) {
      if (value == null) {
        // remove items where value is unset.
        if (this.module.config) {
          this.$delete(this.module.config, id);
          if (Object.keys(this.module.config).length == 0) {
            // remove config completely if it is empty.
            this.$delete(this.module, 'config')
          }
        }
      }
      else {
        if (!this.module.config) {
          this.$set(this.module, 'config', {});
        }
        this.$set(this.module.config, id, value);
      }
      this.$emit("action", "update");
      this.reset_local_config();
    },
    activate_fileinfo(index = null) {
      if (index != null) {
        this.active_fileinfo = index;
      }
      let active_field = this.fileinfos[this.active_fileinfo];
      let value = (active_field) ? ((this.local_config || {})[active_field.id] || []) : [];
      let no_terminal_selected = (this.terminal_id == null);
      this.$emit("action", 'fileinfo_update', { value, no_terminal_selected });
    },
    update_fileinfo(value) {
      let active_field = this.fileinfos[this.active_fileinfo];
      if (active_field) {
        this.changed(active_field.id, value);
      }
    },
    accept_clicked() {
      if (!this.auto_accept.value) {
        this.$set(this.module, 'config', this.local_config);
        this.$emit("action", "update");
      }
      this.$emit("action", "accept_button");
    },
    clear() {
      if (this.auto_accept.value) {
        if (this.module.config) { this.$delete(this.module, 'config') }
        this.reset_local_config();
        this.$emit("action", "update");
        this.$emit("action", "clear");
      }
      else {
        this.local_config = {};
      }
      this.timestamp = Date.now();
    }
  },
  beforeUpdate: function () {
    // reset the active file picker to the first one.
    this.active_fileinfo = 0;
  },
  template
}

export const fieldUI = {};

fieldUI.create_instance = function (target_id) {
  let target = document.getElementById(target_id);
  const FieldsPanelClass = Vue.extend(FieldsPanel);
  this.instance = new FieldsPanelClass({
    data: () => ({
      module: {},
      module_def: {},
      auto_accept: { value: true }
    })
  }).$mount(target);
}