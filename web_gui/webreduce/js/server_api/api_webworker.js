// imports promise worker library
import 'https://unpkg.com/promise-worker/dist/promise-worker.js';

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

var toWrap = ["find_calculated", "get_instrument", "calc_terminal", "list_datasources", "list_instruments", "get_file_metadata", "upload_datafiles"];

toWrap.forEach(function(method_name) {
  server_api[method_name] = wrap_hug_msgpack(method_name);
});

server_api.__init__ = function() {
  const worker = new Worker('worker.js'); // creates a new Worker
  const myPromiseWorker = new PromiseWorker(worker); // creates a new PromiseWorker
  server_api.myPromiseWorker = myPromiseWorker; // assigns the server_api's promise worker to a new PromisWorker
}}


// function sending the find_calculated function to worker.js
server_api.find_calculated = async function () {
  const name = "find_calculated";
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": arguments})
  return result;
}

// function sending the get_instrument function to worker.js
server_api.get_instrument = async function () {
  const name = "get_instrument";
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": arguments})
  return result;
}

// function sending the calc_terminal function to worker.js
server_api.calc_terminal = async function () {
  const name = "calc_terminal";
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": arguments})
  return result;
}

// function sending the list_datasources function to worker.js
server_api.list_datasources = async function () {
  const name = "list_datasources";
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": arguments})
  return result;
}

// function sending the list_instruments function to worker.js
server_api.list_instruments = async function () {
  const name = "list_instruments";
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": arguments})
  return result;
}

// function sending the get_file_metadata function to worker.js
server_api.get_file_metadata = async function () {
  const name = "get_file_metadata";
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": arguments})
  return result;
}

// function sending the get_file_metadata function to worker.js
server_api.upload_datafiles = async function () {
  const name = "upload_datafiles";
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": arguments})
  return result;
}
