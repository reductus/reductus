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
      var r = new Promise(function(resolve, reject) {
        $.jsonRPC.request(method_name, {
          async: true,
          params: params,
          cache: cache,
          success: function(result) {
            resolve(result.result);
          },
          error: function(result) {
            reject({method_name: method_name, params: params, caller: wrapped.caller, resolver: resolve, result: result});
          }
        });
      })
      .catch(function(error) {
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
  
  var toWrap = ["find_calculated", "get_instrument", "calc_terminal", "list_datasources", "list_instruments", "get_file_metadata"];
  toWrap.forEach(function(method_name) {
    app.server_api[method_name] = wrap_jsonRPC(method_name, false);
  });
  
  app.server_api.__init__ = function() {
    return $.getJSON("rpc_config.json", function(config) {
      // get the "parallel_load" suggestion from the rpc_config:
      app.server_api._load_parallel = (config.load_parallel == null) ? false : config.load_parallel;
      var endPoint = "";
      if (config.host != null) {
        endPoint += "//" + config.host + ((config.port == null) ? "" : (":" + config.port.toFixed()));
      } 
      endPoint += "/RPC2";
      $.jsonRPC.setup({
        endPoint: endPoint,
        namespace: '',
        // caching the jquery requests makes no difference because we are using "POST"
        cache: false
      });
    });
  }
})(webreduce);


