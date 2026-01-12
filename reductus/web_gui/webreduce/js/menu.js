import { Vue } from './libraries.js';
import { categoriesEditor } from './ui_components/categories_editor.js';

let template = `
<div class="d-flex flex-column">
  
  <!-- Bootstrap Offcanvas Sidebar -->
  <div class="offcanvas offcanvas-start" :class="{ show: showNavigation }" tabindex="-1">
    <div class="offcanvas-header">
      <h5 class="offcanvas-title"><img src="img/reductus_logo.svg" style="height:2em;"/>Reductus</h5>
      <button type="button" class="btn-close" @click="showNavigation = false"></button>
    </div>
    
    <div class="offcanvas-body p-0">
      <div class="list-group list-group-flush">
        <!-- Template Section -->
        <div class="list-group-item p-0">
          <button class="btn btn-link w-100 text-start p-3 border-bottom" type="button" @click="expandTemplate = !expandTemplate">
            Template
          </button>
          <div v-if="expandTemplate" class="list-group list-group-flush ms-3">
            <button @click="action('new_template')" class="list-group-item list-group-item-action">
              <i class="bi bi-plus me-2"></i> New
            </button>
            <button @click="action('edit_template')" class="list-group-item list-group-item-action">
              <i class="bi bi-pencil me-2"></i> Edit
            </button>
            <button @click="action('download_template')" class="list-group-item list-group-item-action">
              <i class="bi bi-download me-2"></i> Download
            </button>
            <button @click="trigger_upload" class="list-group-item list-group-item-action">
              <i class="bi bi-upload me-2"></i> Upload Template
            </button>
            <div class="list-group-item">
              <label for="predefined_template" class="form-label">Predefined</label>
              <select v-model="predefined_template" class="form-select form-select-sm mb-2" id="predefined_template">
                <option v-for="template in predefined_templates" :value="template">
                  {{template}}
                </option>
              </select>
              <button 
                class="btn btn-primary btn-sm w-100"
                :disabled="predefined_template == ''"
                @click="action('load_predefined', predefined_template)">
                Load
              </button>
            </div>
          </div>
        </div>

        <!-- Data Section -->
        <div class="list-group-item p-0">
          <button class="btn btn-link w-100 text-start p-3 border-bottom" type="button" @click="expandData = !expandData">
            Data
          </button>
          <div v-if="expandData" class="list-group list-group-flush ms-3">
            <button @click="action('stash_data')" class="list-group-item list-group-item-action">
              <i class="bi bi-box-arrow-right me-2"></i> Stash Data
            </button>
            <button @click="showCategoriesEditor(); showNavigation = false" class="list-group-item list-group-item-action">
              <i class="bi bi-list me-2"></i> Edit Categories
            </button>
            <button v-if="enable_uploads" @click="trigger_upload_datafiles" class="list-group-item list-group-item-action">
              <i class="bi bi-briefcase-plus me-2"></i> Upload Datafiles
            </button>
            <button @click="action('export_data')" class="list-group-item list-group-item-action">
              <i class="bi bi-cloud-download me-2"></i> Export
            </button>
            <button @click="trigger_upload" class="list-group-item list-group-item-action">
              <i class="bi bi-upload me-2"></i> Reload Exported
            </button>
            <button @click="action('clear_cache')" class="list-group-item list-group-item-action">
              <i class="bi bi-trash me-2"></i> Clear Cache
            </button>
            <div class="list-group-item">
              <label for="select_datasource" class="form-label">Data Sources</label>
              <select v-model="select_datasource" class="form-select form-select-sm mb-2" id="select_datasource">
                <option v-for="source in datasources" :value="source">
                  {{source}}
                </option>
              </select>
              <button 
                class="btn btn-primary btn-sm w-100"
                @click="action('add_datasource', select_datasource)">
                Add
              </button>
            </div>
          </div>
        </div>

        <!-- Settings Section -->
        <div class="list-group-item p-0">
          <button class="btn btn-link w-100 text-start p-3 border-bottom" type="button" @click="expandSettings = !expandSettings">
            Settings
          </button>
          <div v-if="expandSettings" class="list-group list-group-flush ms-3">
            <div v-for="(setting, setting_name) in settings" class="list-group-item">
              <div class="form-check">
                <input 
                  type="checkbox" 
                  class="form-check-input" 
                  v-model="setting.value" 
                  :id="'setting_' + setting_name"
                />
                <label class="form-check-label" :for="'setting_' + setting_name">
                  {{setting.label}}
                </label>
                <button 
                  class="btn btn-sm btn-link ms-auto" 
                  @click.stop="settingsHelpActiveTab=setting_name; showSettingsHelp = true">
                  <i class="bi bi-info-circle"></i>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Instrument Section -->
        <div class="list-group-item p-0">
          <button class="btn btn-link w-100 text-start p-3 border-bottom" type="button" @click="expandInstrument = !expandInstrument">
            Instrument: <span class="fw-bold">{{current_instrument}}</span>
          </button>
          <div v-if="expandInstrument" class="list-group list-group-flush ms-3">
            <div v-for="instrument in instruments" class="list-group-item d-flex justify-content-between align-items-center">
              <span>{{instrument}}</span>
              <button class="btn btn-primary btn-sm" @click.stop="action('switch_instrument', instrument)">
                switch
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Settings Help Modal -->
  <div class="modal" :class="{ show: showSettingsHelp }" :style="{ display: showSettingsHelp ? 'block' : 'none' }">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Settings</h5>
          <button type="button" class="btn-close" @click="showSettingsHelp = false"></button>
        </div>
        <div class="modal-body">
          <ul class="nav nav-tabs mb-3" role="tablist">
            <li class="nav-item" role="presentation">
              <button 
                class="nav-link" 
                :class="{ active: settingsHelpActiveTab === 'auto_accept' }"
                @click="settingsHelpActiveTab = 'auto_accept'">
                Auto Accept
              </button>
            </li>
            <li class="nav-item" role="presentation">
              <button 
                class="nav-link" 
                :class="{ active: settingsHelpActiveTab === 'check_mtimes' }"
                @click="settingsHelpActiveTab = 'check_mtimes'">
                Auto Reload
              </button>
            </li>
            <li class="nav-item" role="presentation">
              <button 
                class="nav-link" 
                :class="{ active: settingsHelpActiveTab === 'cache_calculations' }"
                @click="settingsHelpActiveTab = 'cache_calculations'">
                Cache
              </button>
            </li>
          </ul>

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
        <div class="modal-footer">
          <button type="button" class="btn btn-primary" @click="showSettingsHelp = false">Close</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal Backdrop -->
  <div v-if="showSettingsHelp" class="modal-backdrop fade show"></div>
  <div v-if="showNavigation" class="offcanvas-backdrop fade show" @click="showNavigation = false"></div>

  <!-- Categories Editor Component -->
  <categories-editor
    ref="categories_editor"
    :categories="categories"
    :default_categories="default_categories"
    :category_keys="category_keys"
    @apply="set_categories">
  </categories-editor>

  <!-- File Upload Inputs -->
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
    categoriesEditor
  },
  props: {
    enable_uploads: Boolean,
    emitter: Object
  },
  data() {
    return {
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
      settingsHelpActiveTab: "auto_accept",
      template_to_upload: null,
      predefined_template: "",
      predefined_templates: [""],
      expandTemplate: true,
      expandData: true,
      expandSettings: false,
      expandInstrument: false,
      settings: {
        auto_accept: { label: "Auto-accept changes", value: true },
        check_mtimes: { label: "Auto-reload newer files", value: false },
        cache_calculations: { label: "Cache calculations", value: true }
      }
    };
  },
  methods: {
    hide() { this.showNavigation = false },
    action(name, argument) {
      this.hide();
      this.emitter.emit("vue_menu.action", name, argument);
    },
    showCategoriesEditor() {
      this.$refs.categories_editor.open();
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

vueMenu.create_instance = function (target_id, propsData={}, emitter=null) {
  let target = document.getElementById(target_id);
  this.instance = Vue.createApp(VueMenu, { ...propsData, emitter }).mount(target);
}