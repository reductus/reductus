// imports promise worker library
import 'https://unpkg.com/promise-worker@2.0.1/dist/promise-worker.js';

import {messagepack as msgpack} from '../libraries.js';
const server_api = {};
export {server_api};

const toWrap = ["find_calculated", "get_instrument", "calc_terminal", "list_datasources", "list_instruments", "get_file_metadata", "upload_datafiles"];

server_api.__init__ = async function(init_progress_obj) {
  const worker = new Worker('/webreduce/js/server_api/worker.js'); // creates a new Worker
  const myPromiseWorker = new PromiseWorker(worker); // creates a new PromiseWorker
  server_api.myPromiseWorker = myPromiseWorker; // assigns the server_api's promise worker to a new PromisWorker
  await server_api.myPromiseWorker.postMessage({"name": "load_pyodide"});
  init_progress_obj.visible = false;
}


// function sending the find_calculated function to worker.js
server_api.find_calculated = async function () {
  const name = "find_calculated";
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": arguments})
  return result;
}

// function sending the get_instrument function to worker.js
server_api.get_instrument = async function () {
  const name = "get_instrument";
  const args_array = [...arguments];
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": args_array});
  return result;
}

// function sending the calc_terminal function to worker.js
server_api.calc_terminal = async function () {
  const name = "calc_terminal";
  const args_array = [...arguments];
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": args_array});
  return result;
}

// function sending the list_datasources function to worker.js
server_api.list_datasources = async function () {
  const name = "list_datasources";
  const args_array = [...arguments];
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": args_array});
  return result;
}

// function sending the list_instruments function to worker.js
server_api.list_instruments = async function () {
  const name = "list_instruments";
  const args_array = [...arguments];
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": args_array})
  return result;
}

// function sending the get_file_metadata function to worker.js
server_api.get_file_metadata = async function () {
  const name = "get_file_metadata";
  const result = await server_api.myPromiseWorker.postMessage({"name": name, "arguments": arguments})
  return result;
}

// function sending the get_file_metadata function to worker.js
server_api.upload_datafiles = async function(files) {
  for (let file of files) {
    const filename = file.name;
    const contents = await file.arrayBuffer();
    const result = await server_api.myPromiseWorker.postMessage({"name": "upload_datafile", "arguments": [contents]});
  }
}