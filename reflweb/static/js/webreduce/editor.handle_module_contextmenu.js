webreduce.editor = webreduce.editor || {};

(function () {
    
  var contextMenuShowing = false;
  
  webreduce.editor.handle_module_contextmenu = function(d,i) {
    if (contextMenuShowing) {
        d3.event.preventDefault();
        d3.select(".popup").remove();
        contextMenuShowing = false;
    } else {
        d3_target = d3.select(d3.event.target);
        var popup;
        
        if (d3_target.classed("title")) {
            d3.event.preventDefault();
            contextMenuShowing = true;

            // Build the popup
            var module_id = d3_target.datum().module_id;
            var module = webreduce.editor._active_template.modules.find(function(m) {return m.module_id == module_id});
            var fields = [];
            if (module && module_defs[module.module] && module_defs[module.module].fields) {
                fields = module_defs[module.module].fields;
            } 
            
            popup = d3.select("#bottom_panel")
            .append("div")
            .attr("class", "popup")
            .style("left", d3.event.x + "px")
            .style("top", d3.event.y + "px")
            .append("ul")
            
            popup.append("li").text("Edit title")
              .on("click", function() {
                d3.select(".popup").remove();
                contextMenuShowing=false;
                var new_title = prompt("New title:", module.title);
                if (new_title != null) {
                  module.title = new_title;
                  d3.select(d3_target.node().parentNode).select('text').text(new_title);
                }                  
              });
            if (fields.length > 0) {
              popup.append("ul").text("Configure:").selectAll('li').data(fields)
                  .enter()
                  .append("li")
                      .text(function(d) {return d.id})
                      .on("click", edit_field(module))
            }
                    
                    
            popup.append("hr")
            popup.append("li").text("delete").on("click", function() {
                console.log(d3_target.datum().module_id);               
                e.svg().datum().modules = e.svg().datum().modules.filter(function(d) { return d.module_id != module_id});
                d3.select(".popup").remove(); 
                e.update();
                contextMenuShowing=false;
            });
        }
                     
    }
  }
})();
