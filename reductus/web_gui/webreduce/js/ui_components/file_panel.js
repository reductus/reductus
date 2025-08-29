import { SourceList } from './sourcelist.js';

let template = `

<div class="filepanel">
  <ul class="nav nav-tabs mb-2">
    <li class="nav-item">
      <button class="nav-link" :class="{active: tab_select === 'data'}" @click="tab_select = 'data'">Raw Data</button>
    </li>
    <li class="nav-item">
      <button class="nav-link" :class="{active: tab_select === 'stashed'}" @click="tab_select = 'stashed'">Stashed</button>
    </li>
  </ul>
  <div v-show="tab_select === 'data'">
    <source-list 
      :datasources="datasources"
      :blocked="blocked"
      ref="sourcelist"
      @checkedChange="handleChecked"
      @pathChange="pathChange"
      @resize="resize"
    ></source-list>
  </div>
  <div v-show="tab_select === 'stashed'">
    <div class="list-group">
      <div class="list-group-item list-group-item-secondary">Compare Stashed</div>
      <div v-for="name in stashnames" class="list-group-item d-flex align-items-center justify-content-between">
        <div class="form-check">
          <input class="form-check-input" type="checkbox" :value="name" v-model="selected_stashes" @change="$emit('action', 'compare_stashed', selected_stashes)">
          <label class="form-check-label">{{name}}</label>
        </div>
        <div class="btn-group">
          <button class="btn btn-outline-secondary btn-sm" @click.stop="$emit('action', 'reload_stash', name)">
            <i class="bi bi-arrow-clockwise"></i> reload
          </button>
          <button class="btn btn-outline-danger btn-sm" @click.stop="$emit('action', 'remove_stash', name)">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
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