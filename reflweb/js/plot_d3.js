function plotD3(data, log_x, log_y) {

    //************************************************************
    // Data notice the structure
    //************************************************************
    var default_data = 	[
	    [{'x':1,'y':0},{'x':2,'y':5},{'x':3,'y':10},{'x':4,'y':0},{'x':5,'y':6},{'x':6,'y':11},{'x':7,'y':9},{'x':8,'y':4},{'x':9,'y':11},{'x':10,'y':2}],
	    [{'x':1,'y':1},{'x':2,'y':6},{'x':3,'y':11},{'x':4,'y':1},{'x':5,'y':7},{'x':6,'y':12},{'x':7,'y':8},{'x':8,'y':3},{'x':9,'y':13},{'x':10,'y':3}],
	    [{'x':1,'y':2},{'x':2,'y':7},{'x':3,'y':12},{'x':4,'y':2},{'x':5,'y':8},{'x':6,'y':13},{'x':7,'y':7},{'x':8,'y':2},{'x':9,'y':4},{'x':10,'y':7}],
	    [{'x':1,'y':3},{'x':2,'y':8},{'x':3,'y':13},{'x':4,'y':3},{'x':5,'y':9},{'x':6,'y':14},{'x':7,'y':6},{'x':8,'y':1},{'x':9,'y':7},{'x':10,'y':9}],
	    [{'x':1,'y':4},{'x':2,'y':9},{'x':3,'y':14},{'x':4,'y':4},{'x':5,'y':10},{'x':6,'y':15},{'x':7,'y':5},{'x':8,'y':0},{'x':9,'y':8},{'x':10,'y':5}]
    ];
    
    var data = (data == null)? default_data : data;
    
    console.log(data, log_x, log_y);
    
    var transformed_data = [];
    var max_y = -Infinity;
    var min_y = Infinity;
    var max_x = -Infinity;
    var min_x = Infinity;
    
    var linf = function(x) { return x }
    var logf = function(x) { return Math.log(x) / Math.LN10 }
    
    var tx = log_x ? logf : linf;
    var ty = log_y ? logf : linf;
    
    var newy, newx;
    
    for (var i=0; i<data.data.length; i++) {
        var newSet = data.data[i].map(
            function(p) {
                newx = tx(p[0]);
                newy = ty(p[1]);
                if (isFinite(newx) && newx > max_x) max_x = tx(p[0]);
                if (isFinite(newx) && newx < min_x) min_x = tx(p[0]);
                if (isFinite(newy) && newy > max_y) max_y = ty(p[1]);
                if (isFinite(newy) && newy < min_y) min_y = ty(p[1]); 
                return {'x': newx, 'y': newy} 
            }
        );
        transformed_data.push(newSet);
    }
    
    data = transformed_data;
    console.log(transformed_data);
    
    var old_colors = [
	    'steelblue',
	    'green',
	    'red',
	    'purple'
    ]

    var colors = [
        "#4bb2c5", 
        "#EAA228", 
        "#c5b47f", 
        "#579575", 
        "#839557", 
        "#958c12", 
        "#953579", 
        "#4b5de4", 
        "#d8b83f", 
        "#ff5800", 
        "#0085cc", 
        "#c747a3", 
        "#cddf54", 
        "#FBD178", 
        "#26B4E3", 
        "#bd70c7"
    ] 
     
    //************************************************************
    // Create Margins and Axis and hook our zoom function
    //************************************************************
    var margin = {top: 20, right: 30, bottom: 30, left: 50},
        width = 960 - margin.left - margin.right,
        height = 500 - margin.top - margin.bottom;
	
    var x = d3.scale.linear()
        .domain([min_x, max_x])
        .range([0, width]);
     
    var y = d3.scale.linear()
        .domain([min_y, max_y])
        .range([height, 0]);
	
    var xAxis = d3.svg.axis()
        .scale(x)
	    .tickSize(-height)
	    .tickPadding(10)	
	    .tickSubdivide(true)	
        .orient("bottom");	
	
    var yAxis = d3.svg.axis()
        .scale(y)
	    .tickPadding(10)
	    .tickSize(-width)
	    .tickSubdivide(true)	
        .orient("left");
	
    var zoom = d3.behavior.zoom()
        .x(x)
        .y(y)
        .scaleExtent([1, 10])
        .on("zoom", zoomed);	
	
	
     
	
	
    //************************************************************
    // Generate our SVG object
    //************************************************************	
    var svg = d3.select("#plot1").append("svg")
	    .call(zoom)
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
	    .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
     
    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);
     
    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis);
     
    svg.append("g")
	    .attr("class", "y axis")
	    .append("text")
	    .attr("class", "axis-label")
	    .attr("transform", "rotate(-90)")
	    .attr("y", (-margin.left) + 10)
	    .attr("x", -height/2)
	    .text('Axis Label');	
     
    svg.append("clipPath")
	    .attr("id", "clip")
	    .append("rect")
	    .attr("width", width)
	    .attr("height", height);
	
	
	
	
	
    //************************************************************
    // Create D3 line object and draw data on our SVG object
    //************************************************************
    var line = d3.svg.line()
        .defined(function(d) { return isFinite(d.y); })
        .interpolate("linear")	
        .x(function(d) { return x(d.x); })
        .y(function(d) { return y(d.y); });		
	
    svg.selectAll('.line')
	    .data(data)
	    .enter()
	    .append("path")
        .attr("class", "line")
	    .attr("clip-path", "url(#clip)")
	    .attr('stroke', function(d,i){ 			
		    return colors[i%colors.length];
	    })
        .attr("d", line);		
	
	
	
	
    //************************************************************
    // Draw points on SVG object based on the data given
    //************************************************************
    var points = svg.selectAll('.dots')
	    .data(data)
	    .enter()
	    .append("g")
        .attr("class", "dots")
	    .attr("clip-path", "url(#clip)");	
     
    points.selectAll('.dot')
	    .data(function(d, index){ 		
		    var a = [];
		    d.forEach(function(point,i){
			    a.push({'index': index, 'point': point});
		    });		
		    return a;
	    })
	    .enter()
	    .append('circle')
	    .attr('class','dot')
	    .attr("r", 2.5)
	    .attr('fill', function(d,i){ 	
		    return colors[d.index%colors.length];
	    })	
	    .attr("transform", function(d) { 
		    return "translate(" + x(d.point.x) + "," + y(d.point.y) + ")"; }
	    );
	
     
	
	
	
	
    //************************************************************
    // Zoom specific updates
    //************************************************************
    function zoomed() {
	    svg.select(".x.axis").call(xAxis);
	    svg.select(".y.axis").call(yAxis);   
	    svg.selectAll('path.line').attr('d', line);  
     
	    points.selectAll('circle').attr("transform", function(d) { 
		    return "translate(" + x(d.point.x) + "," + y(d.point.y) + ")"; }
	    );  
    }
}
