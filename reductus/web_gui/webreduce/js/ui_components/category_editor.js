import { d3 } from '../libraries.js';
import { filebrowser } from '../filebrowser.js';

export function category_editor (categories, default_categories, category_keys) {
  var dialog = $("div#categories_editor").dialog("open");
  var d3_handle = d3.select(dialog[0]);
  var list = d3_handle.select("ol.categories");
  $(list.node()).sortable();

  d3_handle.select("ol.add-more").selectAll("li.add-category").data([1])
    .enter().append("li").classed("add-category", true).style("list-style", "none")
    .append("span").classed("ui-icon ui-icon-circle-plus", true)
    .attr("title", "add category")
  d3_handle.select("ol.add-more").selectAll("li.add-category")
    .on("click", function () {
      var new_data = [[]];
      var new_category = list.insert("li").data([new_data]).classed("category", true);
      add_selectors.call(new_category.node(), new_data);
    })

  function selector(c) {
    //c = c || {value: []};
    //c.value = c.value || [];
    var container = d3.create("span").classed("subcategory", true);
    var sel = container.append("select").classed("subcategory", true);
    sel.selectAll("option").data(c.choices)
      .enter().append("option")
      .attr("value", function (d) { return d[0] })
      .text(function (d) { return d[0] })
    function selection_change() {
      if (this.value != c.value[0]) {
        c.value[0] = this.value;
        c.value.splice(1);
      }
      container.selectAll("span").remove();
      var x = sel.selectAll('option[value="' + this.value + '"]');
      var cc = x.datum()[1];
      if (cc && cc.length) {
        c.value[1] = c.value[1] || [];
        container.selectAll("span.subcategory").data([{ value: c.value[1], choices: cc }]).enter().append(selector);
      }
    }
    if (c.value && c.value[0]) {
      sel.property("value", c.value[0]);
    }
    sel.on("change", selection_change);
    selection_change.call(sel.node());
    return container.node()
  }


  function add_selectors(cl) {
    var citem = d3.select(this);
    var ccontainer = citem.append("span")
      .classed("category-container", true);
    var data = cl.map(function (c) { return { value: c, choices: category_keys.slice() } });
    ccontainer.selectAll("span.category").data(data)
      .enter().append("span").classed("category", true).append(selector)
    citem.append("span").classed("ui-icon ui-icon-circle-plus", true)
      .style("cursor", "pointer")
      .attr("title", "adding keywords on the same row makes a category from\nthe concatenation of the values with a colon (:) separator")
      .on("click", function () {
        cl.push([]);
        var data = cl.map(function (c) { return { value: c, choices: category_keys.slice() } });
        ccontainer.selectAll("span.category").data(data)
          .enter().append("span").classed("category", true)
          .append(selector)
      });
    citem.append("span").classed("ui-icon ui-icon-circle-close", true)
      .style("cursor", "pointer")
      .style("position", "absolute")
      .style("right", "0")
      .attr("title", "remove category")
      .on("click", function () { citem.remove() })
  }

  function set_data(categories) {
    list.selectAll("li.category").remove();

    var categories_nested = categories.map(function (cat) {
      return cat.map(function (v) {
        return v.slice().reverse().reduce(function (a, s) {
          var b = [s]; if (a) { b.push(a) }; return b;
        }, null)
      })
    });

    var citems = list.selectAll("li.category").data(categories_nested)
      .enter().append("li").classed("category", true)
      .style("border", "2px solid grey")
      .style("border-radius", "6px")
      .style("margin-bottom", "4px")
      .style("padding", "2px")

    citems.each(add_selectors);
  }

  set_data(categories);

  // button handlers
  d3_handle.select("button.apply").on("click", function () {
    var rawc = list.selectAll("li.category").data();
    function unpack(nested) {
      var unpacked = [];
      var residual = nested;
      while (residual && residual.length > 0) {
        unpacked.push(residual[0]);
        residual = residual.slice(1)[0];
      }
      return unpacked;
    }
    var unpacked = rawc.map(function (row) {
      return row.map(function (r) {
        return unpack(r)
      })
    });
    categories.splice(0, categories.length, ...unpacked);
    filebrowser.refreshAll();
  })
  d3_handle.select("button.close").on("click", function () { dialog.dialog("close"); });
  d3_handle.select("button.load-defaults").on("click", function () {
    set_data(default_categories);
  });
}