import { SourceList } from './sourcelist.js';

let template = `
<div class="filepanel">
  <md-tabs ref="tabs">
    <md-tab id="navigation" md-label="raw data">
      <source-list 
        :datasources="datasources"
        :blocked="blocked"
        ref="sourcelist"
        @checkedChange="handleChecked"
        @pathChange="pathChange"
        @resize="resize"
      ></source-list>
    </md-tab>
    <md-tab id="stashedlist" md-label="stashed">
      <md-list class="md-dense">
        <md-subheader>Compare Stashed</md-subheader>
        <md-list-item v-for="name in stashnames" :md-disabled="false">
          <md-checkbox 
            v-model="selected_stashes" 
            :value="name"
            class="md-subheading"
            @change="$emit('action', 'compare_stashed', selected_stashes)">
          {{name}}
          </md-checkbox>
          <span class="md-list-item-text"></span>
          <md-button @click.stop="$emit('action', 'reload_stash', name)">
            reload
            <md-icon>launch</md-icon>
          </md-button>
          <md-button class="md-icon-button md-accent" @click.stop="$emit('action', 'remove_stash', name)">
            <md-icon>delete</md-icon>
          </md-button>
          <md-divider/>
        </md-list-item>
      </md-list>
    </md-tab>
  </md-tabs>
</div>
`

export const FilePanel = {
  name: "file-panel",
  components: { SourceList },
  data: () => ({
    datasources: [],
    tab_select: 'data',
    stashnames: [],
    selected_stashes: [],
    blocked: false
  }),
  methods: {
    refreshAll() {
      this.$refs.sourcelist.refreshAll();
    },
    handleChecked() { },
    pathChange() { },
    resize() {
      this.$refs.tabs.calculateTabPos();
    }
  },
  template
}