import {SourceList} from './sourcelist.js';

let template = `
<div class="filepanel">
  <div id="filebrowser_tabselect">
    <label 
      :style="(tab_select == 'data') ? selected_tabstyle : unselected_tabstyle">
      <input type="radio" name="fb_tabs" value="data" v-model="tab_select" checked />
      raw data
    </label>
    <label 
      :style="(tab_select == 'stashed') ? selected_tabstyle : unselected_tabstyle">
      <input type="radio" name="fb_tabs" value="stashed" v-model="tab_select" />
      stashed
    </label>
  </div>
  <div v-show="tab_select == 'data'" id="navigation">
    <source-list 
      :datasources="datasources"
      ref="sourcelist"
      @checkedChange="handleChecked"
      @pathChange="pathChange"
    ></source-list>
  </div>
  <div v-show="tab_select == 'stashed'" id="stashedlist"></div>
</div>
`

export const FilePanel = {
  name: "file-panel",
  components: {SourceList},
  data: () => ({
    datasources: [],
    tab_select: 'data',
    unselected_tabstyle: {
      border: '1px solid grey',
      padding: '0.5em',
      "margin-top": '0.5em',
      "border-bottom": '1px solid grey'
    },
    selected_tabstyle: {
      border: '1px solid grey',
      padding: '0.5em',
      "margin-top": '0.5em',
      "border-bottom": 'none'
    }
  }),
  methods: {
    refreshAll() {
      this.$refs.sourcelist.refreshAll();
    },
    handleChecked() {},
    pathChange() {}
  },
  template
}