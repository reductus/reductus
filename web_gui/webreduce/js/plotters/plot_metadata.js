import { Vue } from '../libraries.js';

let template = `
<div class="metadata-table" style="overflow-x:scroll;">
  <table class="metadata">
    <thead>
      <tr>
        <th v-for="col in cols" :key="col">{{col}}</th>
      </tr>
    </thead>
    <tbody>
      <tr 
        v-for="row in metadata" 
        :key="JSON.stringify(row)"
        class="metadata-row"
        >
        <td v-for="col in cols" :key="col">{{pretty(row[col])}}</td>
      </tr>
    </tbody>
  </table>
</div>
`;

const MetadataTable = {
  name: "metadata-table",
  data: () => ({
    cols: [],
    metadata: [],
    precision: 5
  }),
  methods: {
    pretty(value) {
      if (value && value.toPrecision) {
        return value.toPrecision(this.precision);
      }
      else {
        return value;
      }
    }
  },
  template
}

export function show_plots_metadata(plotdata, plot_controls, target, old_plot) {
  var metadata = plotdata.values.map(function (v) { return v.values });
  var m0 = metadata[0] || {};

  plot_controls.updateShow([]);

  var colset = new Set(Object.keys(m0));
  for (var nm of metadata.slice(1)) {
    for (var c of colset) {
      if (!(c in nm)) {
        colset.delete(c);
      }
    }
  }
  var cols = Array.from(colset);
  while (target.firstChild) {
    // clean out the target
    target.removeChild(target.firstChild);
  }
  target.classList.remove("plot");

  let MetadataTableClass = Vue.extend(MetadataTable);
  let metadata_table = new MetadataTableClass({
    data: () => ({
      cols,
      metadata
    })
  }).$mount(target);
  // let metadata_table = d3.select(target).append("div").append("table").classed("metadata", true)
  // metadata_table
  //   .append("thead").append("tr")
  //   .selectAll(".colHeader")
  //   .data(cols).enter()
  //   .append("th")
  //   .classed("colHeader", true)
  //   .text(function (d) { return String(d) })

  // metadata_table
  //   .append("tbody")
  //   .selectAll(".metadata-row")
  //   .data(metadata).enter()
  //   .append("tr")
  //   .classed("metadata-row", true)
  //   .on("click", function () {
  //     metadata_table.selectAll(".metadata-row")
  //       .classed("active", false);
  //     d3.select(this).classed("active", true);
  //   })
  //   .each(function (d) {
  //     let row = d3.select(this);
  //     cols.forEach(function (c) {
  //       row.append("td").append("pre")
  //         //.attr("contenteditable", true)
  //         //.on("input", function(dd, ii) { 
  //         //  let new_text = this.innerText;
  //         //  let old_text = String(d[c]);
  //         //  let dirty = (old_text != new_text);
  //         //  d3.select(this.parentNode).classed("dirty", dirty);
  //         //})
  //         .text(String(d[c]));
  //     })
  //   });

  return metadata_table
}

