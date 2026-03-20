// Use ESM imports instead of importScripts
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v0.26.1/full/pyodide.mjs";
// import * as Comlink from "https://unpkg.com/comlink/dist/esm/comlink.mjs";
import * as Comlink from "comlink";

let api;
let pyodideInstance;

async function initPyodide() {
  // Initialize Pyodide
  pyodideInstance = await loadPyodide();
  await pyodideInstance.loadPackage(["numpy", "pytz", "h5py", "micropip"]);

  const response = await fetch('./wheel_files.json');
  const local_wheels_text = await response.text();

  // Initialize Reductus API in Python
  api = await pyodideInstance.runPythonAsync(`
  import json
  import micropip
  await micropip.install("orsopy")

  local_wheels = json.loads('${local_wheels_text}')
  for wheel in local_wheels:
      await micropip.install(f"./{wheel}")
  from reductus.web_gui import api

  config = {
    "cache": None,
    "data_sources": [{"name": "local", "url": "file:///", "start_path": "/home/pyodide"}],
    "instruments": ["xrr"]
  }
  api.initialize(config=config)

  def wrap_method(method):
      def wrapper(args):
          args_dict = args.to_py() if args is not None else {}
          return method(**(args_dict or {}))
      return wrapper

  # Map the API methods
  wrapped_api = {m: wrap_method(getattr(api, m)) for m in api.api_methods}
  wrapped_api
  `);
  
  return "loaded";
}

const apiService = {
  async init() {
    return await initPyodide();
  },

  async upload_datafile(filename, contents) {
    // contents is a Uint8Array
    pyodideInstance.FS.writeFile(filename, contents);
    return true;
  },

  async call_api(methodName, args) {
    const pyMethod = api.get(methodName);
    const result = pyMethod(args);
    // Convert Python proxies to JS objects
    return result.toJs({ dict_converter: Object.fromEntries });
  }
};

Comlink.expose(apiService);