let template = `
<div class="patheditor">
  <span v-for="(dir, index) in pathlist" class="pathitem" @click="handle(index)">
    {{dir}}/ 
  </span>
</div>
`

export const PathEditor = {
  name: "path-editor",
  props: ["pathlist"],
  data: () => ({}),
  methods: {
    handle(index) {
      //console.log(index, this.pathlist.slice(0,index+1).join('/'))
      this.$emit("change", this.pathlist.slice(0, index+1));
    }
  },
  template
}