import { treeItem } from './tree_item.js';
import { Sortable } from '../libraries.js';

let template = `
<div>
  <dialog ref="main_dialog" class="categories-editor-dialog" style="width: 800px;">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Categories Editor</h5>
          <button type="button" class="btn-close" @click="close"></button>
        </div>
        
        <div class="modal-body">
          <div style="margin-bottom: 1rem;">
            <div ref="categories_list">
              <template v-for="(category, index) in local_categories" :key="JSON.stringify(category)">
                <div class="card" style="margin: 0.5rem 0; padding: 0.5rem;">
                  <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
                    <div class="d-flex align-items-center flex-wrap gap-2">
                      <span class="handle" style="cursor: grab; color: #666;">≡</span>
                      <template v-for="(sub, subindex) in category" :key="sub.join('.')">
                        <span class="badge bg-primary" style="cursor: pointer;" @click="editSub(index, subindex)">
                          {{sub.join('.')}}
                          <button type="button" @click.stop="removeSub(index, subindex)" style="background: none; border: none; color: inherit; cursor: pointer; margin-left: 0.25rem;">×</button>
                        </span>
                        <span v-if="(subindex < category.length-1)" style="color: #666;">{{settings.subcategory_separator}}</span>
                      </template>
                      <button type="button" class="btn btn-sm btn-outline-primary" @click="addSub(index)">+ Add</button>
                    </div>
                    <div>
                      <button type="button" class="btn btn-sm btn-outline-danger" @click="remove(index)">Remove</button>
                    </div>
                  </div>
                </div>
              </template>
            </div>
            <button type="button" class="btn btn-sm btn-primary mt-2" @click="addCategory">+ Add Category</button>
          </div>
          
          <div class="mb-3">
            <label for="separator_input" class="form-label">Subcategory Separator</label>
            <input type="text" id="separator_input" class="form-control" style="width: 100px;" v-model="settings.subcategory_separator" />
          </div>
        </div>
        
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="reload_defaults">Load Defaults</button>
          <button type="button" class="btn btn-secondary" @click="close">Cancel</button>
          <button type="button" class="btn btn-primary" @click="apply">Apply</button>
          <button type="button" class="btn btn-primary" @click="apply(); close()">Apply and Close</button>
        </div>
      </div>
    </div>
  </dialog>

  <dialog ref="pick_dialog" class="category-picker-dialog" style="width: 500px;">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Select Category</h5>
          <button type="button" class="btn-close" @click="closePick"></button>
        </div>
        
        <div class="modal-body" style="min-height: 500px; max-height: 70vh; overflow-y: auto;">
          <tree-item 
            :item="category_tree"
            @item-picked="pick">
          </tree-item>
        </div>
        
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="closePick">Cancel</button>
        </div>
      </div>
    </div>
  </dialog>
</div>
`

let default_categories = [
  [
    [
      "sample",
      "name"
    ],
    [
      "sample",
      "description"
    ],
    [
      "sample",
      "width"
    ]
  ],
  [
    [
      "intent"
    ]
  ],
  [
    [
      "filenumber"
    ]
  ],
  [
    [
      "polarization"
    ]
  ]
];

let category_keys = [["Qz_basis"], ["angular_resolution"], ["attenuation"], ["channels"], ["columns", [["Qx", [["label"], ["units"]]], ["Qz", [["label"], ["units"]]], ["Qz_target", [["label"], ["units"]]], ["angular_resolution", [["label"], ["units"]]], ["counter.liveMonitor", [["is_scan"], ["label"], ["units"]]], ["counter.liveROI", [["is_scan"], ["label"], ["units"]]], ["counter.liveTime", [["is_scan"], ["label"], ["units"]]], ["counter.monitorPreset", [["is_scan"], ["label"], ["units"]]], ["counter.startTime", [["is_scan"], ["label"], ["units"]]], ["counter.stopTime", [["is_scan"], ["label"], ["units"]]], ["detector/angle_x", [["label"], ["units"]]], ["detector/counts", [["label"], ["units"], ["variance"]]], ["detector/wavelength", [["label"], ["units"], ["variance"]]], ["detectorAngle.softPosition", [["is_scan"], ["label"], ["units"]]], ["flipper1PowerSupply.current", [["is_scan"], ["label"], ["units"]]], ["flipper2PowerSupply.current", [["is_scan"], ["label"], ["units"]]], ["flipper3PowerSupply.current", [["is_scan"], ["label"], ["units"]]], ["flipper4PowerSupply.current", [["is_scan"], ["label"], ["units"]]], ["monitor/count_time", [["label"], ["units"]]], ["monitor/counts", [["label"], ["units"], ["variance"]]], ["monitor/roi_counts", [["label"], ["units"], ["variance"]]], ["monochromator/wavelength", [["label"], ["units"], ["variance"]]], ["q.x", [["is_scan"], ["label"], ["units"]]], ["q.z", [["is_scan"], ["label"], ["units"]]], ["sample/angle_x", [["label"], ["units"]]], ["sampleAngle.softPosition", [["is_scan"], ["label"], ["units"]]], ["slit1/x", [["label"], ["units"]]], ["slit2/x", [["label"], ["units"]]], ["slit3/x", [["label"], ["units"]]], ["slit4/x", [["label"], ["units"]]], ["spinAnalyzerAngle.softPosition", [["is_scan"], ["label"], ["units"]]], ["spinPolarizerAngle.softPosition", [["is_scan"], ["label"], ["units"]]], ["trajectoryData._q", [["is_scan"], ["label"], ["units"]]], ["v", [["errorbars"], ["label"], ["units"]]], ["x", [["errorbars"], ["label"], ["units"]]]]], ["dQ"], ["description"], ["detector", [["angle_x_offset"], ["angle_y"], ["angle_y_offset"], ["columns", [["angle_x", [["units"]]], ["counts", [["units"], ["variance"]]], ["wavelength", [["units"], ["variance"]]]]], ["distance"], ["efficiency"], ["mask"], ["offset_x"], ["offset_y"], ["rotation"], ["saturation"], ["time_of_flight"], ["width_x"], ["width_y"]]], ["duration"], ["dx"], ["entry"], ["filenumber"], ["geometry"], ["instrument"], ["intent"], ["mask"], ["monitor", [["base"], ["columns", [["count_time", [["units"]]], ["counts", [["units"], ["variance"]]], ["roi_counts", [["units"], ["variance"]]]]], ["deadtime"], ["deadtime_error"], ["distance"], ["sampled_fraction"], ["saturation"], ["source_power_units"], ["start_time"], ["time_of_flight"], ["time_step"]]], ["monochromator", [["columns", [["wavelength", [["units"], ["variance"]]]]]]], ["mtime"], ["name"], ["normbase"], ["path"], ["points"], ["polarization"], ["probe"], ["roi", [["xhi"], ["xlo"], ["yhi"], ["ylo"]]], ["sample", [["angle_y"], ["broadening"], ["columns", [["angle_x", [["units"]]]]], ["description"], ["environment", []], ["incident_sld"], ["length"], ["magnet_avg"], ["magnet_setpoint"], ["name"], ["rotation"], ["shape"], ["substrate_sld"], ["temp_avg"], ["temp_setpoint"], ["thickness"], ["width"]]], ["slit1", [["columns", [["x", [["units"]]]]], ["shape"], ["y"], ["y_target"]]], ["slit2", [["columns", [["x", [["units"]]]]], ["shape"], ["y"], ["y_target"]]], ["slit3", [["columns", [["x", [["units"]]]]], ["shape"], ["y"], ["y_target"]]], ["slit4", [["columns", [["x", [["units"]]]]], ["shape"], ["y"], ["y_target"]]], ["uri"], ["vlabel"], ["vscale"], ["vunits"], ["xlabel"], ["xscale"], ["xunits"]];

function annotate(array, id = [1], ancestors=[]) {
  let output = array.map(function (a) {
    let name = a[0];
    let path = [...ancestors, name];
    let child = {
      //id: 'category_picker_' + (id[0] += 1),
      name: name,
      //id: path.join('.'),
      id: JSON.stringify(path)
    }
    if (a.length > 1) {
      child.children = annotate(a[1], id, path);
    }
    return child;
  })
  return output;
}
let category_tree = {name: '/', children: annotate(category_keys)};

export const categoriesEditor = {
  name: "categories-editor",
  components: { 
    treeItem
  },
  props: {
    categories: Array,
    default_categories: Array,
    category_keys: Array
  },
  methods: {
    open() {
      this.$nextTick(() => {
        this.$refs.main_dialog.showModal();
        console.log('opened categories editor', this.categories, this.category_keys);
      });
    },
    removeSub(index, subindex) {
      console.log('removeSub', index, subindex);
      this.local_categories[index].splice(subindex, 1);
    },
    remove(index) {
      this.local_categories.splice(index, 1);
    },
    editSub(index, subindex) {
      console.log('editSub', index, subindex);
      this.pick_category.current_target = {index, subindex};
      this.$nextTick(() => {
        this.$refs.pick_dialog.showModal();
      });
    },
    addSub(index) {
      let category = this.local_categories[index];
      category.push([]);
      this.pick_category.current_target = {index, subindex: (category.length - 1)}
      this.$nextTick(() => {
        this.$refs.pick_dialog.showModal();
      });
    },
    addCategory() {
      let index = (this.local_categories.push([]) - 1);
      this.addSub(index);
    },
    close() {
      this.$refs.main_dialog.close();
      this.$emit('close');
    },
    apply() {
      this.$emit('apply', this.local_categories);
    },
    scrollTop(id) {
      document.getElementById(id).scrollIntoView(true);
    },
    getOpenPath(category) {
      let path = [];
      let parent = category_tree;
      let match = parent;
      for (let c of category) {
        match = parent.find(t => t.name == c);
        path.push(match.id);
        parent = match.children || [];
      }
      return path;
    },
    pick(item) {
      let {index, subindex} = this.pick_category.current_target;
      let subcategory = this.local_categories[index][subindex];
      let new_sub = JSON.parse(item.id);
      subcategory.splice(0, subcategory.length, ...new_sub)
      this.$refs.pick_dialog.close();
    },
    closePick() {
      this.$refs.pick_dialog.close();
    },
    reload_defaults() {
      const default_categories = structuredClone(this.default_categories);
      console.log(default_categories);
      this.local_categories.splice(0, this.local_categories.length, ...default_categories);
    },
    initializeSortable() {
      const container = this.$refs.categories_list;
      if (!container || this.sortable_instance) return;
      
      this.sortable_instance = Sortable.create(container, {
        handle: '.handle',
        animation: 150,
        ghostClass: 'sortable-ghost',
        onEnd: (evt) => {
          const movedItem = this.local_categories[evt.oldIndex];
          this.local_categories.splice(evt.oldIndex, 1);
          this.local_categories.splice(evt.newIndex, 0, movedItem);
        }
      });
    }
  },
  data: () => ({
    disabled: false,
    pick_category: {
      current_target: {index: null, subindex: null},
      current_id: ""
    },
    // TODO:
    // probably don't need another local copy of categories,
    // since the one in the parent is also local (not the canonical version)
    // could just share the array.
    local_categories: default_categories,
    category_tree: category_tree,
    settings: {
      subcategory_separator: ':'
    }
  }),
  mounted() {
    this.initializeSortable();
  },
  updated() {
    this.initializeSortable();
  },
  watch: {
    category_keys: function(old, newVal) {
      const newChildren = annotate(newVal);
      console.log(newChildren);
      console.log(this.category_tree);
      this.category_tree.children.splice(0, this.category_tree.children.length, ...newChildren);
    },
    categories: function(old, newVal) {
      const newCopy = structuredClone(newVal);
      this.local_categories.splice(0, this.local_categories.length, ...newCopy);
    }
  },
  template: template
}