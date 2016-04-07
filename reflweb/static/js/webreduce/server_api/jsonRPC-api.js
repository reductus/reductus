// require(jQuery.jsonRPC)
//
// defines webreduce.server_api for json-rpc
// (wrap the jsonRPC server in a generic API interface)

// all API implementations should provide the functions 
// ["find_calculated", "get_file_metadata", "get_instrument", "calc_terminal"]
// and return a native javascript Promise object from those functions

webreduce = window.webreduce || {};
webreduce.server_api = webreduce.server_api || {};

$.jsonRPC.setup({
  //endPoint: '//localhost:' + rpc_port + '/RPC2',
  endPoint: "http://" + window.location.hostname + ":8001/RPC2",
  namespace: '',
  cache: false
});

(function(app) {
  function wrap_jsonRPC(method_name) {
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
          success: function(result) {
            resolve(result.result);
          },
          error: function(result) {
            reject({method_name: method_name, params: params, caller: wrapped.caller, resolver: resolve, result: result});
          }
        });
      })
      .catch(function(error) {
        // hook in a custom handler
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
  
  var toWrap = ["find_calculated", "get_file_metadata", "get_instrument", "calc_terminal"];
  for (var i=0; i<toWrap.length; i++) {
    var method_name = toWrap[i];
    app.server_api[method_name] = wrap_jsonRPC(method_name);
  }
})(webreduce);


