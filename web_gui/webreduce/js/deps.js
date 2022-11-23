const dependencies = {};
export {dependencies};

function order(template, target) {
    var n, pairs, remaining, processed;
    if (target == null) {
        // Order to evaluate all nodes
        pairs = template.wires.map(function(w) {return [w.source[0], w.target[0]]});
        n = template.modules.length;
    }
    return processing_order(pairs, n)
}

function range(n) {
    return Array.from(new Array(n)).map((u,i) => (i))
}

function processing_order(pairs, n) {
    /*
    Order the work in a workflow.

    Given a set of n items to evaluate numbered from zero through n-1,
    and dependency pairs 


    :Parameters:

    *pairs* : [(int, int), ...]

        Pairwise dependencies amongst items.

    *n* : int

        Number of items, or 0 if we don't care about any item that is not
        mentioned in the list of pairs

    :Returns:

    *order* : [int, ...]

        Permutation which satisfies the partial order requirements.

    */
    var n = (n == null) ? 0 : n;
    var order = _dependencies(pairs);
    if (n > 0) {
        var out_of_range = order.filter(function(id) { return id >= n });
        if (out_of_range.length > 0) {
            //if any(id >= n for id in order):
            throw "Not all dependencies are in the set";
        }
        var order_set = new Set(order);
        var rest = new Set(range(n).filter(function(r) { return (!order_set.has(r)) }));
        //set(range(n)) - set(order)
    }
    else {
        var rest = new Set();
        pairs.forEach(function(p) { p.forEach(function(pp) { rest.add(pp) }) });
        //set(k for p in pairs for k in p) - set(order)
    }
    //print "order",order,"from",pairs
    return order.concat(Array.from(rest.values()));
}


function _dependencies(pairs) {
    //print "order_dependencies",pairs
    var emptyset = new Set();
    var order = []

    // Break pairs into left set and right set
    var left = new Set();
    var right = new Set();
    if (pairs.length > 0) {
        left = new Set(pairs.map(function(p) { return p[0] }));
        right = new Set(pairs.map(function(p) { return p[1] }));
    }
    while (pairs.length > 0) {
        // print "within",pairs
        // Find which items only occur on the right
        var independent = new Set();
        right.forEach(function(r) { if (!left.has(r)) { independent.add(r) } }); 
        if (independent.size == 0) {
            var cycleset = left.values().join(", ")
            throw "Cyclic dependencies amongst " + cycleset
        }

        // The possibly resolvable items are those that depend on the independents
        
        var dependent = new Set(pairs.filter(function(p) { return independent.has(p[1]) }).map(function(p) {return p[0]}))
        //set([a for a, b in pairs if b in independent])
        pairs = pairs.filter(function(p) { return (!independent.has(p[1])) });
        //[(a, b) for a, b in pairs if b not in independent]
        if (pairs.length == 0) {
            var resolved = dependent;
        }
        else {
            left = new Set(pairs.map(function(p) { return p[0] }));
            right = new Set(pairs.map(function(p) { return p[1] }));
            //left, right = [set(s) for s in zip(*pairs)]
            var resolved = new Set();
            dependent.forEach(function(d) { if(!left.has(d)) { resolved.add(d) } });
        }
        //print "independent",independent,"dependent",dependent,"resolvable",resolved
        order = order.concat(Array.from(resolved.values()));
    }
        //print "new order",order
    order.reverse()
    return order
}

function mark_satisfied(template, module_defs) {
    var nodes_ordered = order(template);
    var modules_visited = template.modules.map(function(m) { return false; });
    var modules_satisfied = new Set();
    var modules_unsatisfied = new Set();
    var wires_satisfied = new Set();
    var wires_unsatisfied = new Set();
    
    function get_module_satisfied(node) {
        var module = template.modules[node];
        var external_config = (template.config || {})[node];
        var mdef = module_defs[module.module];
        var inputs_satisfied = mdef.inputs.length == 0 || mdef.inputs.every(function(i) { return get_input_satisfied(node, i.id, mdef) });
        var fileinputs = mdef.fields.filter(function(f) { return f.datatype == 'fileinfo' });
        var fileinputs_satisfied = fileinputs.length == 0 || fileinputs.every(function(f) { 
            var embedded = (module.config && module.config[f.id] && module.config[f.id].length > 0);
            var external = (external_config && external_config[f.id] && external_config[f.id].length > 0);
            return embedded || external;
        });
        var satisfaction = (inputs_satisfied && fileinputs_satisfied);
        if (satisfaction) { modules_satisfied.add(node); }
        else { modules_unsatisfied.add(node) }
        return satisfaction;
    }
    
    function get_input_satisfied(node, terminal_id, mdef) {
        var satisfied_in = [];
        var input_def = mdef.inputs.find(function(idef) { return idef.id == terminal_id });
        template.wires.forEach(function(w, i) { 
            if (w.target[0] == node && w.target[1] == terminal_id) {
                if (modules_satisfied.has(w.source[0])) {
                    wires_satisfied.add(i);
                    satisfied_in.push(i);
                } else {
                    wires_unsatisfied.add(i);
                }
            }
        });
        return (!input_def.required) || satisfied_in.length > 0;
    }
    
    nodes_ordered.forEach(function(n) { return get_module_satisfied(n) });
    
    return {
        modules_satisfied, 
        modules_unsatisfied,
        wires_satisfied,
        wires_unsatisfied
    }
}

dependencies.mark_satisfied = mark_satisfied;
