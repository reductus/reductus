// imports pyodide library
importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.1/full/pyodide.js");
// imports promise worker library
importScripts("https://cdn.jsdelivr.net/npm/promise-worker@2.0.1/dist/promise-worker.register.js");

async function loadPyodideAndPackages() { // loads pyodide
  self.pyodide = await loadPyodide(); // run the function and wait for the result (base library)
  await self.pyodide.loadPackage(["numpy", "pytz", "h5py", "micropip"]); // waits until these python packpages are loaded to continue

  // get local wheels
  const local_wheels = await (await fetch('./wheel_files.json')).text(); // fetches the wheel files from the json file
  console.log({local_wheels});
  //import reductus library with micropip
  let api = await pyodide.runPythonAsync(`
  import json
  import micropip
  await micropip.install("orsopy")

  local_wheels = json.loads('${local_wheels}')
  for wheel in local_wheels:
      await micropip.install(f"./{wheel}")
  from reductus.web_gui import api

  config = {
    "cache": None,
    "data_sources": [
      {
        "name": "local",
        "url": "file:///",
        "start_path": "/home/pyodide"
      }
    ],
    "instruments": [
      "xrr",
    ]
  }

  api.initialize(config=config)

  wrapped_api = {}

  def expose(method):
      def wrapper(args):
          print("args:", args)
          real_kwargs = args.to_py() if args is not None else {}
          return method(**real_kwargs)

      return wrapper

  for method in api.api_methods:
      mfunc = getattr(api, method)
      wrapped = expose(mfunc)
      wrapped_api[method] = wrapped

  wrapped_api
  `);
  return api;
}

let pyodideReadyPromise = loadPyodideAndPackages(); // run the functions stored in lines 4

// await pyodideReadyPromise; // waits for loadPyodideAndPackages to load and run. for the second time it doesn't take anytime

const messageHandler = async function(message) {
  await pyodideReadyPromise;
  const name = message.name;
  const args = message.arguments;
  if (name === 'load_pyodide') {
    let api = await pyodideReadyPromise;
    self.api = api;
    return "loaded";
  }
  else if (name === 'upload_datafile') {
    pyodide.FS.writeFile(args.filename, args.contents); // saves the local file to the file system
  }

  else {
    result = api.get(name)(args);
    return result.toJs({dict_converter: Object.fromEntries}); // converts python args to js
  }

  console.log(message.name) // try this
}

registerPromiseWorker(messageHandler);
