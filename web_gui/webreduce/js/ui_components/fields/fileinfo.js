let template = `
<div class="fileinfo-field">
  <div class="fields">
    <input type="radio" name="fileinfo" :id="field.id" />
    <label :for="field.id" >
      <span class="fileinfo-label">{{field.id + '(' + (value || []).length + ')'}}</span>
    </label>
  </div>
</div>
`;

export const FileinfoUi = {
  name: 'fileinfo-ui',
  props: ["field", "value"],
  template
}

// let update_plots = (datasets_in == null);
//   target.select("#fileinfo input").property("checked", true); // first one
//   target.selectAll("div#fileinfo input")
//     .on("click", function () {
//       filebrowser.fileinfoUpdate(d3.select(this).datum(), update_plots);
//       $(".remote-filebrowser").trigger("fileinfo.update", d3.select(this).datum());
//     });
//   //$("#fileinfo").buttonset();

//   filebrowser.fileinfoUpdate(d3.select("div#fileinfo input").datum(), update_plots);
//   $(".remote-filebrowser").trigger("fileinfo.update", d3.select("div#fileinfo input").datum());
//   // if there is data loaded, an output terminal is selected... and will be plotted instead
//   //if (datasets_in == null) { filebrowser.handleChecked(null, null, true) };
//   return radio
// }
// fieldUI.fileinfo = fileinfoUI;