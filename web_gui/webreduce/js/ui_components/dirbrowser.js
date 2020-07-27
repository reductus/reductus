let template = `
<ul class="dirbrowser">
  <li v-for="subdir in subdirs" :key="subdir" class="subdiritem">
    <span @click="$emit('change', subdir)">(dir) {{subdir}}</span> 
  </li>
</ul>
`

export const DirBrowser = {
  name: "dir-browser",
  props: ["subdirs"],
  template
}