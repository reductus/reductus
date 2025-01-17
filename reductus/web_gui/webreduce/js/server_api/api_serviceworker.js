import {messagepack as msgpack} from '../libraries.js';
const server_api = {};
export {server_api};

function wrap(method_name) {
  async function wrapped(args) {
    var r = new Promise(function(resolve, reject) {
      var xhr = new XMLHttpRequest();
      var endpoint = "/SW/" + method_name;
      xhr.open("POST", endpoint, true);
      
      xhr.setRequestHeader("Content-type", "application/json");
      xhr.setRequestHeader("Accept", "application/msgpack");
      xhr.responseType = "arraybuffer";

      xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE) {
          const responseArray = new Uint8Array(xhr.response);
          console.log(responseArray);
          const decoded = msgpack.decode(responseArray);
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
  server_api[method_name] = wrap(method_name);
});

server_api.__init__ = async function(init_progress_obj) {
  if ('serviceWorker' in navigator) {
    try {
        const registration = await navigator.serviceWorker.register('./sw.js');
        server_api.registration = registration;
        if (navigator.serviceWorker.controller == null) {
            // then it's a hard refresh which has disabled the service worker:
            window.location.reload();
        }
        if (registration.installing) {
                console.log('Service worker installing');
            } else if (registration.waiting) {
                console.log('Service worker installed');
            } else if (registration.active) {
                console.log('Service worker active');
            }
        } catch (error) {
            console.error(`Registration failed with ${error}`);
            return;
        }
    }
    else {
        alert("service workers not supported in this browser (needed for calculation)");
        return;
    }
    // initialize the pyodide:
    const ready = await (await fetch("/SW/load_pyodide")).json();
    console.log({ready});
    init_progress_obj.visible = false;
};

server_api.upload_datafiles = async function(files) {
  console.log('uploading: ', files);
  for (let file of files) {
    const filename = file.name;
    const contents_buf = await file.arrayBuffer(); // converts into binary array
    const contents = new Uint8Array(contents_buf); // changes the type of binary array
    const result = await server_api.registration.active.postMessage({"name": "upload_datafile", "args": {filename, contents}});
  }
}