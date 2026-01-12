import { SourceList } from './sourcelist.js';

let template = `
<div class="filepanel">
  <div class="d-flex flex-column h-100">
    <ul class="nav nav-tabs" role="tablist" style="flex-shrink: 0;">
      <li class="nav-item" role="presentation">
        <button 
          class="nav-link active" 
          id="navigation-tab" 
          data-bs-toggle="tab" 
          data-bs-target="#navigation" 
          type="button" 
          role="tab">
          raw data
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button 
          class="nav-link" 
          id="stashedlist-tab" 
          data-bs-toggle="tab" 
          data-bs-target="#stashedlist" 
          type="button" 
          role="tab">
          stashed
        </button>
      </li>
    </ul>

    <div class="tab-content flex-grow-1 overflow-auto">
      <div class="tab-pane fade show active" id="navigation" role="tabpanel">
        <source-list 
          :datasources="datasources"
          :blocked="blocked"
          ref="sourcelist"
          @checkedChange="handleChecked"
          @pathChange="pathChange"
          @resize="resize"
        ></source-list>
      </div>
      
      <div class="tab-pane fade" id="stashedlist" role="tabpanel">
        <div class="p-3">
          <h6 class="mb-3">Compare Stashed</h6>
          <div class="list-group">
            <div v-for="name in stashnames" :key="name" class="list-group-item">
              <div class="d-flex align-items-center gap-2">
                <input 
                  type="checkbox" 
                  class="form-check-input" 
                  :id="'stash_' + name"
                  v-model="selected_stashes" 
                  :value="name"
                  @change="emitter.emit('filebrowser.action', 'compare_stashed', selected_stashes)"
                >
                <label class="form-check-label flex-grow-1 mb-0" :for="'stash_' + name">
                  {{name}}
                </label>
                <button 
                  type="button" 
                  class="btn btn-sm btn-outline-primary" 
                  @click.stop="emitter.emit('filebrowser.action', 'reload_stash', name)">
                  <i class="mdi mdi-launch" style="margin-right: 0.25rem;"></i>reload
                </button>
                <button 
                  type="button" 
                  class="btn btn-sm btn-outline-danger" 
                  @click.stop="emitter.emit('filebrowser.action', 'remove_stash', name)">
                  <i class="mdi mdi-delete"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
`

export const FilePanel = {
  name: "file-panel",
  components: { SourceList },
  props: {
    emitter: Object,
    onPathChange: Function,
    onHandleChecked: Function
  },
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
    handleChecked(values) {
      if (this.onHandleChecked) {
        this.onHandleChecked(values);
      }
    },
    pathChange(source, pathlist, datasourceIndex) {
      if (this.onPathChange) {
        this.onPathChange(source, pathlist, datasourceIndex);
      }
    },
    resize() {
      // Bootstrap tabs don't need manual position calculation
      // This method is kept for compatibility but does nothing
    }
  },
  template
}