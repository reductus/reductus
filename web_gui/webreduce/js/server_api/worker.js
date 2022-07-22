// imports pyodide library
importScripts("https://cdn.jsdelivr.net/pyodide/v0.20.0/full/pyodide.js");
// imports promise worker library
importScripts("https://cdn.jsdelivr.net/npm/promise-worker@2.0.1/dist/promise-worker.register.js");

async function loadPyodideAndPackages() { // loads pyodide
  self.pyodide = await loadPyodide(); // run the function and wait for the result (base library)
  await self.pyodide.loadPackage(["numpy", "pytz", "micropip"]); // waits until these python packpages are loaded to continue

  //import reductus library with micropip
  let api = await pyodide.runPythonAsync(`
  import micropip
  await micropip.install("./reductus-0.9.0-py3-none-any.whl")
  from web_gui import api
  
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
    pyodide.FS.writeFile(args.filename, args.contents);
  }
  
  else {
    result = api.get(name)(args);
    return result.toJs({dict_converter: Object.fromEntries});
  }

  console.log(message.name) // try this
}

registerPromiseWorker(messageHandler);
