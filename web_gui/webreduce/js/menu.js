import { Vue, VueMaterial } from './libraries.js';

let template = `
<div class="page-container md-layout-column">

  <md-drawer :md-active.sync="showNavigation" md-swipeable>
    <md-toolbar class="md-transparent" md-elevation="0">
      <span class="md-title">My App name</span>
    </md-toolbar>

    <md-list>
      <md-list-item md-expand>
        <md-icon>mediation</md-icon>
        <span class="md-list-item-text">Template</span>
        <md-list slot="md-expand">
          <md-list-item @click="action('new_template')" class="md-inset">
            <span class="md-list-item-text">New</span>
            <md-icon class="md-primary">add</md-icon>      
          </md-list-item>
          <md-list-item @click="action('edit_template')" class="md-inset">
            <span class="md-list-item-text">Edit</span>
            <md-icon class="md-primary">edit</md-icon>      
          </md-list-item>
          <md-list-item @click="action('download_template')" class="md-inset">
            <span class="md-list-item-text">Download</span>
            <md-icon class="md-primary">get_app</md-icon>      
          </md-list-item>
          <md-list-item class="md-inset">
            <md-field>
              <label>Upload Template</label>
              <md-file 
                v-model="template_to_upload" 
                @change="action('upload_template', $event.target.files[0]); template_to_upload=null;"/>
            </md-field>
            <md-icon class="md-primary">publish</md-icon>      
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
      
      <md-list-item md-expand>
        <md-icon>source</md-icon>
        <span class="md-list-item-text">Data</span>
        <md-list slot="md-expand">
          <md-list-item @click="action('stash_data')" class="md-inset">
            <span class="md-list-item-text">Stash Data</span>
            <md-icon class="md-primary">input</md-icon>
          </md-list-item>
          <md-list-item @click="action('edit_categories')" class="md-inset">
            <span class="md-list-item-text">Edit Categories</span>
            <md-icon class="md-primary">list</md-icon>      
          </md-list-item>
          <md-list-item @click="action('export_data')" class="md-inset">
            <span class="md-list-item-text">Export</span>
            <md-icon class="md-primary">cloud_download</md-icon>      
          </md-list-item>
          <md-list-item @click="hide(); reload_exported()" class="md-inset">
            <span class="md-list-item-text">Reload Exported</span>
            <md-icon class="md-primary">cloud_upload</md-icon>      
          </md-list-item>
          <md-list-item @click="hide(); clear_cache()" class="md-inset">
            <span class="md-list-item-text">Clear Cache</span>
            <md-icon class="md-primary">remove_circle</md-icon>      
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
              @click="hide();add_datasource(source)">
              Add
            </md-button>
          </md-list-item>
        </md-list>  
      </md-list-item>

      <md-list-item md-expand>
        <md-icon>settings</md-icon>
        <span class="md-list-item-text">Settings</span>
        <md-list slot="md-expand">
          <md-list-item class="md-inset">
            <md-checkbox v-model="settings.auto_accept" class="md-primary" />
            <span class="md-list-item-text">Auto-accept changes</span>
            <md-button class="md-icon-button" @click.stop="settingsHelpActiveTab='auto_accept'; showSettingsHelp = true">
              <md-icon class="md-primary">info</md-icon>
            </md-button>
          </md-list-item>
          <md-list-item class="md-inset">
            <md-checkbox v-model="settings.check_mtimes" class="md-primary" />
            <span class="md-list-item-text">Auto-reload modified files</span>
            <md-button class="md-icon-button" @click.stop="settingsHelpActiveTab='check_mtimes'; showSettingsHelp = true">
              <md-icon class="md-primary">info</md-icon>
            </md-button>
          </md-list-item>
          <md-list-item class="md-inset">
            <md-checkbox v-model="settings.cache_calculations" class="md-primary" />
            <span class="md-list-item-text">Cache calculations</span>
            <md-button class="md-icon-button" @click.stop="settingsHelpActiveTab='cache_calculations'; showSettingsHelp = true">
              <md-icon class="md-primary">info</md-icon>
            </md-button>
          </md-list-item>
        </md-list>
      </md-list-item>

      <md-list-item md-expand>
        <md-icon>biotech</md-icon>
        <div class="md-list-item-text">Instrument: <span class="md-title">{{current_instrument}}</span></div>
        <md-list slot="md-expand">
          <md-list-item class="md-inset" v-for="instrument in instruments">
            <span class="md-list-item-text">{{instrument}}</span>
            <md-button class="md-raised md-primary" @click.stop="hide(); switch_instruments(instrument)">
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

  
</div >
`;

export const VueMenu = {
  name: 'vue-menu',
  data: () => ({
    current_instrument: "ncnr.refl",
    instruments: ["ncnr.refl", "ncnr.sans", "ncnr.vsans"],
    datasources: ["ncnr", "charlotte"],
    select_datasource: "ncnr",
    showNavigation: false,
    showSettingsHelp: false,
    settingsHelpActiveTab: "",
    template_to_upload: null,
    predefined_template: "complex",
    predefined_templates: [
      "simple", "complex"
    ],
    stash_name: null,
    settings: {
      auto_accept: true,
      check_mtimes: true,
      cache_calculations: true
    }
  }),
  methods: {
    hide() { this.showNavigation = false },
    action(name, argument) {
      this.hide();
      this.$emit("action", name, argument);
    },
    new_template: nop
  },
  watch: {
    predefined_templates: {
      handler: function(val, oldVal) {
        this.predefined_template = val[0] || "";
      },
      deep: true
    }
  },
  template
}

function nop(x) {console.log(x)};

export const vueMenu = {};

vueMenu.create_instance = function (target_id) {
  Vue.use(VueMaterial);
  let target = document.getElementById(target_id);
  const VueMenuClass = Vue.extend(VueMenu);
  this.instance = new VueMenuClass({
    data: () => ({
      showNavigation: true
    })
  }).$mount(target);
}