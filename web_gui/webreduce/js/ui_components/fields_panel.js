import { Vue } from '../libraries.js';
import { Components } from './fields/index.js';

let template = `
<div class="fields-panel">
  <h3>{{ module_def.name }}</h3>
  <button @click="help">help</button>
  <div 
    class="fields"
    v-for="(field, index) in module_def.fields"
    :key="JSON.stringify(field)"
    >
    <component 
      v-bind:is="field.datatype + '-ui'" 
      :field="field"
      :value="config[field.id]"
      class="item-component">
    </component>
  </div>
  <div class="control-buttons" style="position:absolute;bottom:10px;">
    <button class="accept config" @click="accept">{{(auto_accept) ? "replot" : "accept"}}</button>
    <button class="clear config" @click="clear">clear</button>
  </div>
</div>
`

export const FieldsPanel = {
  name: "fields-panel",
  components: Components,
  data: () => ({
    module_def: {},
    config: {},
    auto_accept: true
  }),
  methods: {
    help() {
      let helpwindow = window.open("", "help", "location=0,toolbar=no,menubar=no,scrollbars=yes,resizable=yes,width=960,height=480");
      helpwindow.document.title = "Web reduction help";
      helpwindow.document.write(this.module_def.description);
      helpwindow.document.close();
      if (helpwindow.MathJax) {
        helpwindow.MathJax.Hub.Queue(["Typeset", helpwindow.MathJax.Hub]);
      }
    },
    field_value(field_id) {
      return config[field_id];
    },
    accept() {
      // editor.accept_parameters(config_target, active_module);
      // if (selected_terminal.empty()) {
      //   // then it's a loader that's clicked, with no output selected;
      //   let first_output = module_def.outputs[0].id;
      //   let selected_title = editor_select.select("g.module g.title.selected");
      //   let module_elem = d3.select(selected_title.node().parentNode);
      //   module_elem.selectAll("g.terminals").classed('selected', function (d) { return d.id == first_output });
      // }
      // else if (!(selected_terminal.classed("output"))) {
      //   // find the first output and select that one...
      //   let first_output = module_def.outputs[0].id;
      //   let module_elem = d3.select(selected_terminal.node().parentNode.parentNode);
      //   module_elem.selectAll("g.terminals").classed('selected', function (d) { return d.id == first_output });
      // }
      // module_clicked_single();
    },
    clear() {
      if (this.active_module.config) { delete this.active_module.config }
      this.$emit("clear"); 
      //module_clicked_single();
    }
  },
  template
}

export const fieldUI = {};

fieldUI.create_instance = function(target_id) {
  let target = document.getElementById(target_id);
  const FieldsPanelClass = Vue.extend(FieldsPanel);
  this.instance = new FieldsPanelClass({
    data: () => ({
      module_def: {},
      config: {},
      auto_accept: true
    })
  }).$mount(target);
}