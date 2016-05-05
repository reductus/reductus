// require(jQuery.jsonRPC)
//
// defines webreduce.server_api for json-rpc
// (wrap the jsonRPC server in a generic API interface)

// all API implementations should provide the functions 
// ["find_calculated", "get_file_metadata", "get_instrument", "calc_terminal"]
// and return a native javascript Promise object from those functions

webreduce = window.webreduce || {};
webreduce.server_api = webreduce.server_api || {};

(function(app) {
  function wrap_jsonRPC(method_name, cache) {
    function wrapped() {
      // pass every argument to the wrapped function as a list:
      var params = [];
      for (var i=0; i<arguments.length; i++) {
        // this excludes the extra properties in arguments that aren't
        // array-like.
        params[i] = arguments[i];
      }
      $.blockUI();
      var r = new Promise(function(resolve, reject) {
        $.jsonRPC.request(method_name, {
          async: true,
          params: params,
          cache: cache,
          success: function(result) {
            $.unblockUI();
            resolve(result.result);
          },
          error: function(result) {
            $.unblockUI();
            reject({method_name: method_name, params: params, caller: wrapped.caller, resolver: resolve, result: result});
          }
        });
      })
      .catch(function(error) {
        // hook in a custom handler
        $.unblockUI();
        if (app.api_exception_handler) {
          app.api_exception_handler(error); 
        } else {
          throw(error);
        }
      });
      return r
    }
    return wrapped
  }
  
  var toWrap_cached = ["find_calculated", "get_instrument", "calc_terminal", "list_datasources", "list_instruments"];
  var toWrap_uncached = ["get_file_metadata"];
  toWrap_cached.forEach(function(method_name) {
    app.server_api[method_name] = wrap_jsonRPC(method_name, true);
  });
  toWrap_uncached.forEach(function(method_name) {
    app.server_api[method_name] = wrap_jsonRPC(method_name, false);
  });
  
  app.server_api.__init__ = function() {
    return $.getJSON("rpc_config.json", function(config) {
      $.jsonRPC.setup({
        //endPoint: '//localhost:' + rpc_port + '/RPC2',
        endPoint: "http://" + config.host + ":" + config.port.toFixed() + "/RPC2",
        namespace: '',
        // this gets explicitly set for each call, but by default make it true:
        cache: true
      });
    });
  }
})(webreduce);


