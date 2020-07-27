import {Tree} from '../libraries.js';
import {PathEditor} from './patheditor.js';
import {DirBrowser} from './dirbrowser.js';

let template = `
<div class="datasource">
  <div class="buttons">
    <button @click="uncheck_all">uncheck all</button>
    <button @click="$emit('remove', index)">remove</button>
    <button @click="$emit('refresh', index)">refresh</button>
  </div> 
  <path-editor :pathlist="source.pathlist" @change="new_subpath"></path-editor>
  <dir-browser :subdirs="source.subdirs" @change="new_subdir"></dir-browser>
  <div class="filetree" ref="tree"></div>
</div>
`

export const DataSource = {
  name: "data-source",
  components: {PathEditor, DirBrowser},
  props: ["source", "index"],
  data: () => ({
    tree: null
  }),
  methods: {
    new_subdir(subdir) {
      this.$emit("change", this.source.name, this.source.pathlist.concat(subdir), this.index);
    },
    new_subpath(subpath) {
      this.$emit("change", this.source.name, subpath, this.index);
    },
    set_treedata(treedata) {
      this.tree = new Tree(this.$refs.tree, {
        data: treedata,
        closeDepth: -1,
        itemClickToggle: 'closed',
        onChange: (v) => {this.$emit("checked")}
      })
      //this.tree.onChange = () => this.$emit("checked");
    },
    get_checked() {
      return this.tree && this.tree.values;
    },
    set_checked(values) {
      if (this.tree) {
        let to_set = values.filter(v => (v in this.tree.leafNodesById));
        this.tree.values = to_set;
      }
    },
    uncheck_all() {
      this.set_checked([]);
      this.$emit("checked");
    }
  },
  mounted: function() {
    //this.tree = new Tree(this.$refs.tree.$el, this.source.treedata);
    //console.log(this.source.treedata);
    // go get tree data
    this.set_treedata(this.source.treedata);
  },
  template
}