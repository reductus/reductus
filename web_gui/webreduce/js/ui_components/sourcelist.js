import { DataSource } from './datasource.js';

let template = `
<div class="sourcelist">
  <div><button id="refresh_all" @click="refreshAll">refresh all</button></div>
  <div style="position: relative">
    <div :class="{'block-overlay': blocked}"></div>
    <data-source 
      v-for="(source, index) in datasources" 
      :source="source" 
      :index="index" 
      :key="source.name + ':' + source.pathlist.join('/') + ':' + JSON.stringify(source.treedata)"
      @change="pathChange"
      @remove="remove"
      @refresh="refresh"
      @checked="checked"
      @open-close="$emit('resize')"
      ref="sources"
    ></data-source>
  </div>
</div>
`

export const SourceList = {
  name: "source-list",
  components: { DataSource },
  props: ["datasources", "blocked"],
  methods: {
    pathChange(source, new_pathlist, index) {
      this.$emit("pathChange", source, new_pathlist, index);
    },
    remove(index) {
      this.$delete(this.datasources, index);
    },
    refresh(index) {
      let s = this.datasources[index];
      this.$emit("pathChange", s.name, s.pathlist, index);
    },
    refreshAll() {
      this.datasources.forEach((d,i) => this.refresh(i));
    },
    set_treedata(index, treedata) {
      this.$refs.sources[index].set_treedata(treedata);
    },
    get_checked() {
      return this.$refs.sources.map(s => s.get_checked());
    },
    checked() {
      // re-emit for all sources
      this.$emit("checkedChange", this.get_checked().flat());
    },
    async set_checked(values) {
      // make sure we're mounted...
      await this.$nextTick();
      (this.$refs.sources || []).forEach(s => (s.set_checked(values)));
    }
  },
  template
}