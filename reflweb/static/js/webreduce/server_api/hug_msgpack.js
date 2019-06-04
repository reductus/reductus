import {app} from '../main.js';
const server_api = {};
export {server_api};

function wrap_hug_msgpack(method_name) {
  function wrapped(args) {
    var r = new Promise(function(resolve, reject) {
      var xhr = new XMLHttpRequest();
      var endpoint = "/RPC2/" + method_name;
      xhr.open("POST", endpoint, true);
      
      xhr.setRequestHeader("Content-type", "application/json");
      xhr.responseType = "arraybuffer";

      xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE) {
          var responseArray = new Uint8Array(xhr.response),
          decoded = msgpack.decode(responseArray);
          ((xhr.status == 200) ? resolve : reject)(decoded);
        }
      }
      xhr.send(JSON.stringify(args) || "");
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
  server_api[method_name] = wrap_hug_msgpack(method_name);
});
  
server_api.__init__ = function() { return Promise.resolve(true); }