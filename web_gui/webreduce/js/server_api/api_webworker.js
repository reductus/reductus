// imports promise worker library
importScripts('https://unpkg.com/promise-worker/dist/promise-worker.js');

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
  PromiseWorker = require('promise-worker'); // GO OVER
  const worker = new Worker('worker.js'); // creates a new Worker
  const myPromiseWorker = new PromiseWorker(worker); // creates a new PromiseWorker
  server_api.myPromiseWorker = myPromiseWorker; // assigns the server_api's promise worker to a new PromisWorker


  // addButton.addEventListener("click", (event) => {
  //   let one = document.getElementById("firstInput").value;
  //   let two = document.getElementById("secondInput").value;
  //
  //   worker.postMessage([one, two]); // main js script sends a message to worker
  // });

  // worker.onmessage = function(message) { // main js script recieves a message from worker
  //   document.getElementById("printSum").innerHTML = message.data;
}}


// function sending the find_calculated function to worker.js
server_api.find_calculated = async function () {
  const result = await server_api.myPromiseWorker.postMessage({"name": "find_caculated", "arguments": arguments})
  return result
  const name = "find_calculated";
}

// function sending the get_instrument function to worker.js
server_api.get_instrument = async function () {
  const result = await server_api.myPromiseWorker.postMessage({"name": "get_instrument", "arguments": arguments})
  return result
  const name = "get_instrument";
}

// function sending the calc_terminal function to worker.js
server_api.calc_terminal = async function () {
  const result = await server_api.myPromiseWorker.postMessage({"name": "calc_terminal", "arguments": arguments})
  return result
  const name = "calc_terminal";
}

// function sending the list_datasources function to worker.js
server_api.list_datasources = async function () {
  const result = await server_api.myPromiseWorker.postMessage({"name": "list_datasources", "arguments": arguments})
  return result
  const name = "list_datasources";
}

// function sending the list_instruments function to worker.js
server_api.list_instruments = async function () {
  const result = await server_api.myPromiseWorker.postMessage({"name": "list_instruments", "arguments": arguments})
  return result
  const name = "list_instruments";
}

// function sending the get_file_metadata function to worker.js
server_api.get_file_metadata = async function () {
  const result = await server_api.myPromiseWorker.postMessage({"name": "get_file_metadata", "arguments": arguments})
  return result
  const name = "get_file_metadata";
}

// function sending the get_file_metadata function to worker.js
server_api.upload_datafiles = async function () {
  const result = await server_api.myPromiseWorker.postMessage({"name": "upload_datafiles", "arguments": arguments})
  return result
  const name = "upload_datafiles";
}
