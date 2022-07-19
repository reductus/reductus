import {messagepack as msgpack} from '../libraries.js';
const server_api = {};
export {server_api};

function wrap_hug_msgpack(method_name) {
  async function wrapped(args) {
    var r = new Promise(function(resolve, reject) {
      var xhr = new XMLHttpRequest();
      var endpoint = "/RPC2/" + method_name;
      xhr.open("POST", endpoint, true);
      
      xhr.setRequestHeader("Content-type", "application/json");
      xhr.setRequestHeader("Accept", "application/msgpack");
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
      if (server_api.exception_handler) {
        server_api.exception_handler(error); 
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
  
const sleep = (seconds) => new Promise(r => setTimeout(r, seconds * 1000));

server_api.__init__ = async function(init_progress_obj) { 
  init_progress_obj.status_text = "Loading pyodide...";
  await sleep(1);
  console.log('loading 1');
  init_progress_obj.status_text += "\nLoading numpy...";
  await sleep(2);
  console.log('loading 2');
  init_progress_obj.status_text += "\nLoading scipy...";
  await sleep(10);
  console.log('loading 3');
  init_progress_obj.visible = false;
  return true;
}

server_api.upload_datafiles = async function(files) {
  window.uploaded_files = window.uploaded_files ?? {};
  for (let file of files) {
    console.log(file.name);
    const filename = file.name;
    const contents = await file.arrayBuffer();
    window.uploaded_files[file.name] = contents; 
  }
  console.log(files.length);
}