import { Vue } from './libraries.js';
import { categoriesEditor } from './ui_components/categories_editor.js';
import { DropdownMenu } from './ui_components/dropdown_menu.js';

let template = `

<div>
  <nav class="navbar navbar-light px-2" style="background-color: #ffff00;">
      <div class="d-flex align-items-center w-100">
        <a class="navbar-brand d-flex align-items-center me-3" href="#">
          <img src="img/reductus_logo.svg" style="height:2em;" alt="Reductus logo"/>
          <span class="ms-2">Reductus</span>
        </a>
        <div class="d-flex flex-row gap-2 align-items-center">
      <dropdown-menu label="Template">
        <a class="dropdown-item" href="#" @click="action('new_template')">
          <i class="bi bi-file-earmark-plus me-2"></i>New
        </a>
        <a class="dropdown-item" href="#" @click="action('edit_template')">
          <i class="bi bi-pencil-square me-2"></i>Edit
        </a>
        <a class="dropdown-item" href="#" @click="action('download_template')">
          <i class="bi bi-download me-2"></i>Download
        </a>
        <a class="dropdown-item" href="#" @click="trigger_upload">
          <i class="bi bi-upload me-2"></i>Upload Template
        </a>
        <div class="px-3 py-2">
          <label for="predefined_template">Predefined</label>
          <select v-model="predefined_template" name="predefined_template" id="predefined_template" class="form-select mb-2">
            <option v-for="template in predefined_templates" :value="template">{{template}}</option>
          </select>
          <button class="btn btn-primary w-100" :disabled="predefined_template == ''" @click="action('load_predefined', predefined_template)">
            <i class="bi bi-box-arrow-in-down me-2"></i>Load
          </button>
        </div>
      </dropdown-menu>
      <dropdown-menu label="Data">
        <a class="dropdown-item" href="#" @click="action('stash_data')">
          <i class="bi bi-box-arrow-right me-2"></i>Stash Data
        </a>
        <a class="dropdown-item" href="#" @click="showCategoriesEditor = true; showNavigation = false">
          <i class="bi bi-list-ul me-2"></i>Edit Categories
        </a>
        <a v-if="enable_uploads" class="dropdown-item" href="#" @click="trigger_upload_datafiles">
          <i class="bi bi-briefcase me-2"></i>Upload Datafiles
        </a>
        <a class="dropdown-item" href="#" @click="action('export_data')">
          <i class="bi bi-cloud-download me-2"></i>Export
        </a>
        <a class="dropdown-item" href="#" @click="trigger_upload">
          <i class="bi bi-arrow-repeat me-2"></i>Reload Exported
        </a>
        <a class="dropdown-item" href="#" @click="action('clear_cache')">
          <i class="bi bi-trash me-2"></i>Clear Cache
        </a>
        <div class="px-3 py-2">
          <label for="select_datasource">Data Sources</label>
          <select v-model="select_datasource" name="select_datasource" id="select_datasource" class="form-select mb-2">
            <option v-for="source in datasources" :value="source">{{source}}</option>
          </select>
          <button class="btn btn-primary w-100" @click="action('add_datasource', select_datasource)">
            <i class="bi bi-plus-lg me-2"></i>Add
          </button>
        </div>
      </dropdown-menu>
      <dropdown-menu label="Settings">
        <div v-for="(setting, setting_name) in settings" class="dropdown-item d-flex align-items-center">
          <i class="bi bi-gear me-2"></i>
          <input type="checkbox" v-model="setting.value" class="form-check-input me-2" />
          <span>{{setting.label}}</span>
          <button class="btn btn-link btn-sm ms-auto" @click.stop="settingsHelpActiveTab=setting_name; showSettingsHelp = true">
            <i class="bi bi-info-circle"></i>
          </button>
        </div>
      </dropdown-menu>
      <dropdown-menu :label="'Instrument: ' + current_instrument">
        <div v-for="instrument in instruments" class="dropdown-item d-flex justify-content-between align-items-center">
          <i class="bi bi-diagram-3 me-2"></i>
          <span>{{instrument}}</span>
          <button class="btn btn-primary btn-sm" @click.stop="action('switch_instrument', instrument)">
            <i class="bi bi-arrow-left-right me-1"></i>switch
          </button>
        </div>
      </dropdown-menu>
    </div>
        <div class="ms-auto d-flex align-items-center gap-3">
          <a href="https://doi.org/10.5281/zenodo.3524406" target="_blank" class="text-decoration-none me-2" title="Cite Reductus">
            <i class="bi bi-journal-text me-1"></i>Cite
          </a>
          <img src="img/NCNR_nonlogo.png" alt="NCNR logo" title="NIST Center for Neutron Research" style="height:2em;padding-right:1.5em;">
          <img src="img/nist-logo.svg" alt="NIST logo" title="National Institute of Standards and Technology" style="height:2em;">
        </div>
      </div>
  </nav>

  <!-- Native Dialog for Settings Help -->
  <dialog v-if="showSettingsHelp" open class="modal-dialog modal-lg" style="max-width:768px;">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Settings</h5>
        <button type="button" class="btn-close" @click="showSettingsHelp = false"></button>
      </div>
      <div class="modal-body">
        <ul class="nav nav-tabs" role="tablist">
          <li class="nav-item" v-for="(setting, setting_name) in settings" :key="setting_name">
            <button class="nav-link" :class="{'active': settingsHelpActiveTab === setting_name}" @click="settingsHelpActiveTab = setting_name">{{setting.label}}</button>
          </li>
        </ul>
        <div class="tab-content mt-3">
          <div v-if="settingsHelpActiveTab === 'auto_accept'">
            <p>If checked, any changes to values in the parameter panel are immediately applied to the template.</p>
            <p>If unchecked, the user must press the "Accept" button after changing numbers in a panel</p>
          </div>
          <div v-if="settingsHelpActiveTab === 'check_mtimes'">
            <p>If checked, when a calculation is requested the last-modified times of all files to be loaded are compared to the most recent available files from the datasource</p>
            <p>If a newer version of any of the files is available, the newer version is loaded and used for the calculation</p>
            <p>If unchecked, the datasource is not queried for last-modified times</p>
          </div>
          <div v-if="settingsHelpActiveTab === 'cache_calculations'">
            <p>If checked, all calculations requested from the server are locally cached.
              When a new calculation is requested, the request is compared to previous 
              requests and if there is a match the cached data is used and no request 
              is made to the server
            </p>
            <p>If unchecked, all calculation requests are sent to the server</p>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-primary" @click="showSettingsHelp = false">Close</button>
      </div>
    </div>
  </dialog>

  <!-- Categories Editor (unchanged, still a Vue component) -->
  <categories-editor 
    :dialog="showCategoriesEditor" 
    :categories="categories"
    :default_categories="default_categories"
    :category_keys="category_keys"
    @close="showCategoriesEditor=false"
    @apply="set_categories">
  </categories-editor>

  <!-- File Inputs -->
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
</div>
`;

export const VueMenu = {
  name: 'vue-menu',
  components: {
    categoriesEditor,
    DropdownMenu
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
    },
    // From app_header
    api_error: {
      visible: false,
      message: ""
    },
    init_progress: {
      visible: true,
      status_text: "Loading pyodide backend..."
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
    },
    // From app_header
    show_api_error(message) {
      this.api_error.message = message;
      this.api_error.visible = true;
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