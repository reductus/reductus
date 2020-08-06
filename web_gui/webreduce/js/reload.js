const signatures = {
  json: [123, 10], // just the {\n characters
  column: [35,34,116,101,109,112,108,97,116,101,95,100,97,116,97,34,58], // #"template_data":
  hdf5: [137,72,68,70,13,10,26,10],
  png: [137,80,78,71,13,10,26,10]
}

function get_type(contents) {
  let [type, test] = Object.entries(signatures).find(([n,t]) => (
    t.every((c,i) => (contents[i] == c))
  ))
  return type
}

const readers = {};

readers.json = function(contents) {
  let text = new TextDecoder('utf-8').decode(contents);
  let template = JSON.parse(text);
  return {template}
}

readers.column = function(contents) {
  let text = new TextDecoder('utf-8').decode(contents);
  let first_return = text.indexOf('\n');
  // remove signature and truncate at first carriage return
  let trimmed = text.slice(17,first_return);
  return JSON.parse(trimmed);
}

export function reload(contents) {
  let content_type = get_type(contents);
  if (content_type in readers) {
    return readers[content_type](contents)
  }
}