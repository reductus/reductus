// imports pyodide library
importScripts("https://cdn.jsdelivr.net/pyodide/v0.20.0/full/pyodide.js");
// imports promise worker library
importScripts('https://unpkg.com/promise-worker@2.0.1/dist/promise-worker.register.js');

async function loadPyodideAndPackages() { // loads pyodide
  self.pyodide = await loadPyodide(); // run the function and wait for the result (base library)
  await self.pyodide.loadPackage(["numpy", "pytz", "micropip"]); // waits until these python packpages are loaded to continue

  //import reductus library with micropip
  await pyodide.runPythonAsync(`
  import micropip
  await micropip.install("./reductus-0.9.0-py3-none-any.whl")
  from web_gui import api
  `)
}

let pyodideReadyPromise = loadPyodideAndPackages(); // run the functions stored in lines 4

// await pyodideReadyPromise; // waits for loadPyodideAndPackages to load and run. for the second time it doesn't take anytime

const messageHandler = async function(message) {
  const name = message.name;
  if (name === 'load_pyodide') {
    await pyodideReadyPromise;
    return "loaded";
  }

    console.log(message.name) // try this
}

registerPromiseWorker(messageHandler);
