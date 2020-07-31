import { extend } from '../../libraries.js';

let field_template = `
<div class="fields">
  <label>
    {{field.label}}
    <div 
      class="patch" 
      v-for="(patch, index) in local_value"
      :key="JSON.stringify(patch)"
      >
      {{JSON.stringify(patch)}}
      <button style="color:red;font-weight:bold;">x</button>
    ></div>
  </label>
  <div class="patch-key">
    Key: {{field.typeattr.key}}
  </div>
</div>
`;

export const PatchUi = {
  name: 'patch-ui',
  props: ["field", "value", "add_interactors"],
  data: () => ({
    local_value: extend(true, [], value)
  }),
  field_template
}

// var active_plot = plotter.instance.active_plot;
//     cols = active_plot.selectAll("th.colHeader").data();
//     key_col = cols.indexOf(key);
//     active_plot.selectAll(".metadata-row")
//       .each(function(d,i) { 

//         d3.select(this).selectAll("pre")
//           .attr("contenteditable", function(dd, ii) {
//             return ii != key_col;
//           })
//           .attr("title", function(dd, ii) {
//             let c = cols[ii];
//             return "was: " + d[c];
//           })
//           .on("input", function(dd, ii) {
//             let c = cols[ii];
//             let new_text = this.innerText;
//             let old_text = String(d[c]);
//             let dirty = (old_text != new_text);
//             d3.select(this.parentNode).classed("dirty", dirty);
//             let path = "/" + d[key] + "/" + c;
//             var p = {path: path, value: new_text, op: op}
//             let update_existing = false;
//             if (dirty) {
//               for (var po of datum.value) {
//                 if (po.path == path) {
//                   po.value = new_text;
//                   update_existing = true;
//                   break;
//                 }
//               }
//               if (!update_existing) {
//                 datum.value.push(p);
//               }
//             }
//             else {
//               for (var vi in datum.value) {
//                 let po = datum.value[vi];
//                 if (po.path == path) {
//                   datum.value.splice(vi, 1);
//                   break;
//                 }
//               }
//             }
//             input.selectAll("li.patches").data(datum.value).enter()
//               .append("li")
//               .classed("patches", true)
              
//             input.selectAll("li.patches").data(datum.value).exit().remove()
            
//             input.selectAll("li.patches")
//               .text(function(d) { return JSON.stringify(d)})

//             var event = document.createEvent('Event');
//             event.initEvent('input', true, true);
//             input.node().dispatchEvent(event);
//           })
//           .each(function(dd, ii) {
//             let c = cols[ii];
//             let path = "/" + d[key] + "/" + c;
//             let match_patch = datum.value.find(function(v) { return v.path == path });
//             if (match_patch) {
//               d3.select(this).text(String(match_patch.value))
//               d3.select(this.parentNode).classed("dirty", true);
//             }
//           })
//       });