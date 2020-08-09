/* adapted from https://vuejs.org/v2/examples/tree-view.html */

let template = `
<li>
  <div
    :class="{bold: isFolder}"
    @click="toggle">
    <span v-if="isFolder">
    {{ item.name }}
    [{{ isOpen ? '-' : '+' }}]
    </span>
    <a 
      style="cursor:pointer;" 
      v-else
      @click="$emit('item-picked', item)"
      >{{item.name}}</a>
  </div>
  <ul v-show="isOpen" v-if="isFolder">
    <tree-item
      class="item"
      v-for="(child, index) in item.children"
      :key="child.id || index"
      :class="child.class"
      :item="child"
      @item-picked="$emit('item-picked', $event)"
    ></tree-item>
  </ul>
</li>
`;

export const treeItem = {
  name: "tree-item",
  props: {
    item: Object
  },
  data: () => ({
    isOpen: false
  }),
  computed: {
    isFolder: function() {
      return this.item.children && this.item.children.length;
    }
  },
  methods: {
    toggle: function() {
      if (this.isFolder) {
        this.isOpen = !this.isOpen;
      }
    }
  },
  template
}