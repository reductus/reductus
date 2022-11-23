const signatures = [
  ['json', [123]], // just the { character
  ['column', [35,34,116,101,109,112,108,97,116,101,95,100,97,116,97,34,58]], // #"template_data":
  ['column', [35,32,34,116,101,109,112,108,97,116,101,95,100,97,116,97,34,58]], // # "template_data":
  ['hdf5', [137,72,68,70,13,10,26,10]],
  ['png', [137,80,78,71,13,10,26,10]]
];

const MAX_SIGNATURE_LENGTH = Math.max.apply(null, signatures.map(s => s[1].length));

async function get_type(file) {
  let slice = file.slice(0, MAX_SIGNATURE_LENGTH);
  let header = await slice.arrayBuffer();
  let header_array = new Uint8Array(header);
  let [type, test] = signatures.find(([n,t]) => (
    t.every((c,i) => (header_array[i] == c))
  ))
  return type
}

const readers = {};

readers.json = function(contents) {
  let text = new TextDecoder('utf-8').decode(contents);
  let template = JSON.parse(text);
  return {template}
}

readers.column = function(contents, sig_length) {
  let text = new TextDecoder('utf-8').decode(contents);
  let first_return = text.indexOf('\n');
  // truncate at first carriage return and
  // remove signature:
  let trimmed = text.slice(0, first_return);
  trimmed = trimmed.replace(/^#\s?"template_data":/, "");
  return JSON.parse(trimmed);
}

export async function reload(file) {
  let content_type = await get_type(file);
  let contents = await file.arrayBuffer();
  if (content_type in readers) {
    return readers[content_type](contents)
  }
}