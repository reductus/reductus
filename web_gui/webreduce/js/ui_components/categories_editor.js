import { treeItem } from './tree_item.js';
import { extend, vuedraggable } from '../libraries.js';

let template = `
<div>
  <md-dialog :md-active="dialog">
    <md-card>
      <md-card-header>
        <div class="md-title">Categories Editor</div>
      </md-card-header>
      <md-card-content>
        <draggable v-model="local_categories">
          <template v-for="(category, index) in local_categories">
            <md-card :key="JSON.stringify(category)" style="margin:8px;padding:0.5em;">
              <div class="md-layout md-alignment-center-space-between">
                <div class="md-layout-item">
                  <md-icon class="handle" style="cursor:grab;">reorder</md-icon>
                  <template v-if="true" v-for="(sub, subindex) in category">
                    <md-chip 
                      :key="sub.join('.')"
                      md-clickable
                      md-deletable
                      @click.stop="editSub(index, subindex)"
                      @md-delete.stop="removeSub(index, subindex)"
                      >
                      {{sub.join('.')}}
                    </md-chip>
                    <span v-if="(subindex < category.length-1)">{{settings.subcategory_separator}}</span>
                  </template>
                  <md-button @click="addSub(index)" class="md-icon-button md-dense">
                    <md-icon class="md-primary">add</md-icon>
                  </md-button>
                </div>
                <div>
                  <md-button @click="remove(index)" class="md-layout-item md-icon-button md-dense md-accent">
                    <md-icon>cancel</md-icon>
                  </md-button>
                </div>
              </div>
            </md-card>
          </template>
        </draggable>
        <md-button @click="addCategory" class="md-layout-item md-icon-button md-dense md-raised md-primary">
          <md-icon>add</md-icon>
        </md-button>
        <md-field>
          <label>subcategory separator</label>
          <md-input outlined v-model="settings.subcategory_separator" :style="{width: 5}" />
        </md-field>
      </md-card-content>
      <md-dialog-actions>
        <md-button class="md-primary" @click="reload_defaults">Load Defaults</md-button>
        <md-button class="md-raised md-accent" @click="close">Cancel</md-button>
        <md-button class="md-raised md-primary" @click="apply">Apply</md-button>
        <md-button class="md-raised md-primary" @click="apply(); close()">Apply and Close</md-button>
      </md-dialog-actions>
    </md-card>
  </md-dialog>

  <md-dialog scrollable persistent :md-active="pick_category.open" max-width="500px">
    <md-dialog-title>Select Category</md-dialog-title>
    <md-dialog-content>
      <md-card>      
        <md-card-content style="min-height:500px;max-height: 90%;">
          <tree-item 
            :item="category_tree"
            @item-picked="pick">
          </tree-item>
        </md-card-content>
      </md-card>  
    </md-dialog-content>
    <md-dialog-actions>
      <md-button class="md-accent md-raised" @click="pick_category.open = false">cancel</md-button>
    </md-dialog-actions>
  </md-dialog>
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
    treeItem,
    draggable: vuedraggable
  },
  props: {
    dialog: {
      default: false
    },
    categories: Array,
    default_categories: Array,
    category_keys: Array
  },
  methods: {
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
      this.pick_category.open = true;
    },
    addSub(index) {
      let category = this.local_categories[index];
      category.push([]);
      this.pick_category.current_target = {index, subindex: (category.length - 1)}
      this.pick_category.open = true;
    },
    addCategory() {
      let index = (this.local_categories.push([]) - 1);
      this.addSub(index);
    },
    close() {
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
      this.pick_category.open = false;
    },
    reload_defaults() {
      let default_categories = extend(true, [], this.default_categories);
      console.log(default_categories);
      this.local_categories.splice(0, this.local_categories.length, ...default_categories);
    }
  },
  data: () => ({
    disabled: false,
    dialog_open: true,
    pick_category: {
      open: false,
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
  watch: {
    category_keys: function(old, newVal) {
      let newChildren = annotate(newVal);
      this.category_tree.children.splice(0, this.category_tree.children.length, ...newChildren);
    },
    categories: function(old, newVal) {
      let newCopy = extend(true, [], newVal);
      this.local_categories.splice(0, this.local_categories.length, ...newCopy);
    }
  },
  template: template
}