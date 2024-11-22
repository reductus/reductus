import { Vue } from './libraries.js';
import { categoriesEditor } from './ui_components/categories_editor.js';

let template = `
<div class="page-container md-layout-column">
  
  <md-drawer :md-active.sync="showNavigation" md-swipeable>
    <md-toolbar class="md-transparent" md-elevation="0">
      <span class="md-title"><img src="img/reductus_logo.svg" style="height:2em;"/>Reductus</span>
    </md-toolbar>

    <md-list>
      <md-list-item md-expand md-expanded>
        <md-icon md-src="img/mediation-black-18dp.svg"></md-icon>
        <span class="md-list-item-text md-title">Template</span>
        <md-list slot="md-expand">
          <md-list-item @click="action('new_template')" class="md-inset">
            <span class="md-list-item-text">New</span>
            <md-icon class="mdi mdi-plus md-primary"></md-icon>
          </md-list-item>
          <md-list-item @click="action('edit_template')" class="md-inset">
            <span class="md-list-item-text">Edit</span>
            <md-icon class="mdi mdi-pencil md-primary"></md-icon>
          </md-list-item>
          <md-list-item @click="action('download_template')" class="md-inset">
            <span class="md-list-item-text">Download</span>
            <md-icon class="mdi mdi-download md-primary"></md-icon>
          </md-list-item>
          <md-list-item @click="trigger_upload" class="md-inset">
            <span class="md-list-item-text">Upload Template</span>
            <md-icon class="mdi mdi-upload md-primary"></md-icon>
          </md-list-item>
          <md-list-item class="md-inset md-double-line">
            <md-field>
            <label for="predefined_template">Predefined</label>
            <md-select v-model="predefined_template" name="predefined_template" id="predefined_template">
              <md-option v-for="template in predefined_templates" :value="template">
                {{template}}
              </md-option>
            </md-select>
            </md-field>
            <md-button 
              class="md-raised md-primary"
              :disabled="predefined_template == ''"
              @click="action('load_predefined', predefined_template)">
              Load
            </md-button>
          </md-list-item>
        </md-list>
      </md-list-item>
      
      <md-list-item md-expand md-expanded>
        <md-icon md-src="img/source-black-18dp.svg"></md-icon>
        <span class="md-list-item-text md-title">Data</span>
        <md-list slot="md-expand">
          <md-list-item @click="action('stash_data')" class="md-inset">
            <span class="md-list-item-text">Stash Data</span>
            <md-icon class="mdi mdi-arrow-right-bold-box-outline md-primary"></md-icon>
          </md-list-item>
          <md-list-item @click="showCategoriesEditor = true; showNavigation = false" class="md-inset">
            <span class="md-list-item-text">Edit Categories</span>
            <md-icon class="mdi mdi-format-list-bulleted md-primary"></md-icon>
          </md-list-item>
          <md-list-item v-if="enable_uploads" @click="trigger_upload_datafiles" class="md-inset">
            <span class="md-list-item-text">Upload Datafiles</span>
            <md-icon class="mdi mdi-briefcase-upload md-primary"></md-icon>
          </md-list-item>
          <md-list-item @click="action('export_data')" class="md-inset">
            <span class="md-list-item-text">Export</span>
            <md-icon class="mdi mdi-cloud-download md-primary"></md-icon>
          </md-list-item>
          <md-list-item @click="trigger_upload" class="md-inset">
            <span class="md-list-item-text">Reload Exported</span>
            <md-icon class="mdi mdi-upload md-primary"></md-icon>
          </md-list-item>
          <md-list-item @click="action('clear_cache')" class="md-inset">
            <span class="md-list-item-text">Clear Cache</span>
            <md-icon class="mdi mdi-delete-circle md-primary"></md-icon>
          </md-list-item>
          <md-list-item class="md-inset">
            <md-field>
            <label for="select_datasource">Data Sources</label>
            <md-select v-model="select_datasource" name="select_datasource" id="select_datasource">
              <md-option v-for="source in datasources" :value="source">
                {{source}}
              </md-option>
            </md-select>
            </md-field>
            <md-button 
              class="md-raised md-primary"
              @click="action('add_datasource', select_datasource)">
              Add
            </md-button>
          </md-list-item>
        </md-list>  
      </md-list-item>

      <md-list-item md-expand>
        <md-icon class="mdi mdi-cog"></md-icon>
        <span class="md-list-item-text md-title">Settings</span>
        <md-list slot="md-expand">
          <md-list-item v-for="(setting, setting_name) in settings" class="md-inset">
            <md-checkbox v-model="setting.value" class="md-primary" />
            <span class="md-list-item-text">{{setting.label}}</span>
            <md-button class="md-icon-button" @click.stop="settingsHelpActiveTab=setting_name; showSettingsHelp = true">
              <md-icon class="mdi mdi-information-outline md-primary"></md-icon>
            </md-button>
          </md-list-item>
        </md-list>
      </md-list-item>

      <md-list-item md-expand>
        <md-icon md-src="img/biotech-black-18dp.svg"></md-icon>
        <div class="md-list-item-text">Instrument: <span class="md-title">{{current_instrument}}</span></div>
        <md-list slot="md-expand">
          <md-list-item class="md-inset" v-for="instrument in instruments">
            <span class="md-list-item-text">{{instrument}}</span>
            <md-button class="md-raised md-primary" @click.stop="action('switch_instrument', instrument)">
              switch
            </md-button>
          </md-list-item>
        </md-list>
      </md-list-item>
    </md-list>
  </md-drawer>

  <md-dialog :md-active.sync="showSettingsHelp" style="max-width:768px;">
    <md-dialog-title>Settings</md-dialog-title>

    <md-tabs :md-active-tab.sync="settingsHelpActiveTab" md-dynamic-height>
      <md-tab id="auto_accept" md-label="Auto Accept">
        <p>If checked, any changes to values in the parameter panel are immediately applied to the template.</p>
        <p>If unchecked, the user must press the "Accept" button after changing numbers in a panel</p>
      </md-tab>

      <md-tab id="check_mtimes" md-label="Auto Reload">
        <p>If checked, when a calculation is requested the last-modified times of all files to be loaded are compared to the most recent available files from the datasource</p>
        <p>If a newer version of any of the files is available, the newer version is loaded and used for the calculation</p>
        <p>If unchecked, the datasource is not queried for last-modified times</p>
        </md-tab>

      <md-tab id="cache_calculations" md-label="Cache">
        <p>If checked, all calculations requested from the server are locally cached.
           When a new calculation is requested, the request is compared to previous 
           requests and if there is a match the cached data is used and no request 
           is made to the server
        </p>
        <p>If unchecked, all calculation requests are sent to the server</p>
      </md-tab>
    </md-tabs>

    <md-dialog-actions>
      <md-button class="md-primary" @click="showSettingsHelp = false">Close</md-button>
    </md-dialog-actions>
  </md-dialog>

  <categories-editor 
    :dialog="showCategoriesEditor" 
    :categories="categories"
    :default_categories="default_categories"
    :category_keys="category_keys"
    @close="showCategoriesEditor=false"

    @apply="set_categories">
  </categories-editor>

  <input 
    ref="upload_template" 
    type="file" 
    multiple="false" 
    id="upload_template" 
    name="upload_template" 
    style="display:none;"
    @change="upload"
  />

  <input 
    ref="upload_datafiles" 
    type="file" 
    multiple="true" 
    id="upload_datafiles" 
    name="upload_datafiles" 
    style="display:none;"
    @mousedown="function() {this.value=''}"
    @change="upload_datafiles"
  />
  
</div >
`;

export const VueMenu = {
  name: 'vue-menu',
  components: {
    categoriesEditor
  },
  props: ['enable_uploads'],
  data: () => ({
    current_instrument: "ncnr.refl",
    instruments: ["ncnr.refl", "ncnr.sans", "ncnr.vsans"],
    datasources: ["ncnr", "charlotte"],
    categories: [],
    default_categories: [],
    category_keys: [],
    select_datasource: "ncnr",
    showNavigation: false,
    showSettingsHelp: false,
    showApiError: false,
    APIErrorMessage: "",
    showCategoriesEditor: false,
    settingsHelpActiveTab: "",
    template_to_upload: null,
    predefined_template: "",
    predefined_templates: [""],
    stash_name: null,
    settings: {
      auto_accept: { label: "Auto-accept changes", value: true },
      check_mtimes: { label: "Auto-reload newer files", value: false },
      cache_calculations: { label: "Cache calculations", value: true }
    }
  }),
  methods: {
    hide() { this.showNavigation = false },
    action(name, argument) {
      this.hide();
      this.$emit("action", name, argument);
    },
    new_template: nop,
    set_categories(new_categories) {
      this.categories.splice(0, this.categories.length, ...new_categories);
      this.$emit("action", 'set_categories', this.categories);
    },
    async upload(ev) {
      this.action('upload_file', ev.target.files[0]);
      ev.target.value = "";
      await(this.$nextTick());
      this.template_to_upload = null;
    },
    async upload_datafiles(ev) {
      this.action('upload_datafiles', ev.target.files);
    },
    trigger_upload() {
      this.$refs.upload_template.click();
    },
    trigger_upload_datafiles() {
      this.$refs.upload_datafiles.click();
    }
  },
  watch: {
    predefined_templates: {
      handler: function (val, oldVal) {
        this.predefined_template = val[0] || "";
      },
      deep: true
    }
  },
  template
}

function nop(x) { console.log(x) };

export const vueMenu = {};

vueMenu.create_instance = function (target_id, propsData={}) {
  let target = document.getElementById(target_id);
  const VueMenuClass = Vue.extend(VueMenu);
  this.instance = new VueMenuClass({
    data: () => ({
      showNavigation: false
    }), 
    propsData,
  }).$mount(target);
}