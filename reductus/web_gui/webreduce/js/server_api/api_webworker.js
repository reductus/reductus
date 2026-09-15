import * as Comlink from 'comlink';

const server_api = {};
export { server_api };

let remoteApi;

server_api.__init__ = async function(header_instance) {
  const worker = new Worker(
    new URL('./worker.js', import.meta.url),
    { type: 'module' } // Essential if your worker uses 'import' statements
  );
  // Wrap the worker with Comlink
  remoteApi = Comlink.wrap(worker);
  
  // Call the init method on the worker
  await remoteApi.init();

  if (header_instance && header_instance.close_init_progress) {
    header_instance.close_init_progress();
  }
};

/**
 * Helper to handle the standard API calls.
 * This dynamically calls 'call_api' on the worker.
 */
const makeApiCall = (methodName) => {
  return async (args) => {
    console.log(`Calling API method: ${methodName} with args:`, args);
    return await remoteApi.call_api(methodName, args);
  };
};

// Define the methods listed in your original "toWrap" array
const methods = [
  "find_calculated", "get_instrument", "calc_terminal", 
  "list_datasources", "list_instruments", "get_file_metadata",
  "get_startup_banner"
];

methods.forEach(method => {
  server_api[method] = makeApiCall(method);
});

// Specialized logic for multi-file upload
server_api.upload_datafiles = async function(files) {
  for (let file of files) {
    const filename = file.name;
    const contents_buf = await file.arrayBuffer();
    const contents = new Uint8Array(contents_buf);
    
    // Transfer the large Uint8Array buffer instead of copying it for performance
    await remoteApi.upload_datafile(
      filename, 
      Comlink.transfer(contents, [contents.buffer])
    );
  }
};