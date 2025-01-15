// sw.js

// Setup your project to serve `py-worker.js`. You should also serve
// `pyodide.js`, and all its associated `.asm.js`, `.data`, `.json`,
// and `.wasm` files as well:
importScripts("https://cdn.jsdelivr.net/npm/xhr-shim@0.1.3/src/index.js");
self.XMLHttpRequest = self.XMLHttpRequestShim;
importScripts("https://cdn.jsdelivr.net/pyodide/v0.21.3/full/pyodide.js");

let pyodide = null;
const context = {
  pyodide: null,
  api: null,
}

async function loadPyodideAndPackages() {
  console.log('trying to load Pyodide');
  const pyodide = await loadPyodide();
  context.pyodide = pyodide;
  await pyodide.loadPackage(["numpy", "pytz", "msgpack", "micropip"]);
  const api = await pyodide.runPythonAsync(`
  import micropip
  import msgpack
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
          try:
              output = method(**real_kwargs)
              return msgpack.dumps(output)
          except Exception as e:
              return msgpack.dumps({'error': str(e)})

      return wrapper

  for method in api.api_methods:
      mfunc = getattr(api, method)
      wrapped = expose(mfunc)
      wrapped_api[method] = wrapped
      print("wrapped: ", method)

  wrapped_api
  `)
  context.api = api;
  return api
}

 
self.addEventListener("install", () => {
  console.log('installing');
  self.skipWaiting();
  context.pyodideReadyPromise = loadPyodideAndPackages();
  context.pyodideReadyPromise.then(() => {
    console.log("install finished from sw.js side");
  });
})

self.addEventListener("activate", function (event) {
  event.waitUntil((async () => {
    await self.pyodideReadyPromise;
    await self.clients.claim();
    self.clients.matchAll().then(clients => {
      clients.forEach(client => client.postMessage("ready"));
    });
    console.log("clients claimed");
  })());
});

self.addEventListener("message", async function(message) {
  const { data: { name, args } } = message;
  console.log({name, args});
  await context.pyodideReadyPromise;
  if (name === 'upload_datafile') {
    result = await context.pyodide.FS.writeFile(args.filename, args.contents); // saves the local file to the file system
    console.log({result});
  }
});

self.addEventListener("fetch", async (event) => {
  console.log(event.request.url);
  const action_search = /\/SW\/(.*)$/.exec(event.request.url);
  console.log(action_search);
  const action = action_search?.[1];
  if (action) {
    console.log(action);
    if (action == 'load_pyodide') {
      event.respondWith(make_ready());
    }
    else if (action == 'upload_datafile') {
      context.pyodide.FS.writeFile(args.filename, args.contents); // saves the local file to the file system
    }
    else {
      event.respondWith(do_api_call(action, event));
    }
  }
});

async function make_ready() {
  if (!context?.api) {
    await loadPyodideAndPackages();
  }
  return new Response("true", { headers: { 'Content-Type': 'application/json' } });
}

async function do_api_call(action, event) {
  const raw_args = await event.request.text();
  args = (raw_args == "") ? null : JSON.parse(raw_args);
  console.log(args);
  const result = context.api.get(action)(args);
  const js_result = result.toJs({dict_converter: Object.fromEntries});
  console.log(result);
  console.log({js_result});
  return new Response(js_result, { headers: { 'Content-Type': 'application/msgpack' } });
}

async function do_calculation(event) {
  try {
    const json_data = await event.request.text();
    let python = `
      request = json.loads('${json_data}')
      form = FakeFieldStorage(request)
      json.dumps(nact.cgi_call(form))
    `;
    let results = await self.pyodide.runPythonAsync(python);
    return new Response(results, { headers: { 'Content-Type': 'application/json' } });
  }
  catch (error) {
    const edata = JSON.stringify({ success: false, detail: {error: error.message }});
    return new Response(edata, {headers: {'Content-Type': 'application/json'}});
  }
}