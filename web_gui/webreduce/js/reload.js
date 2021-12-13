import { yaml_load } from './libraries.js';

const signatures = [
  ['json', [123]], // just the { character
  ['column', [35,34,116,101,109,112,108,97,116,101,95,100,97,116,97,34,58]], // #"template_data":
  ['column', [35,32,34,116,101,109,112,108,97,116,101,95,100,97,116,97,34,58]], // # "template_data":
  ['hdf5', [137,72,68,70,13,10,26,10]],
  ['png', [137,80,78,71,13,10,26,10]],
  ['orso', [35,32,35,32,79,82,83,79,32,114,101,102,108,101,99,116,105,118,105,116,121,32,100,97,116,97,32,102,105,108,101]]
];

function get_type(contents) {
  let [type, test] = signatures.find(([n,t]) => (
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

readers.column = function(contents, sig_length) {
  let text = new TextDecoder('utf-8').decode(contents);
  let first_return = text.indexOf('\n');
  // truncate at first carriage return and
  // remove signature:
  let trimmed = text.slice(0, first_return);
  trimmed = trimmed.replace(/^#\s?"template_data":/, "");
  return JSON.parse(trimmed);
}

readers.orso = function(contents) {
  let text = new TextDecoder('utf-8').decode(contents);
  let lines = text.split("\n");
  if (/YAML encoding/.test(lines[0])) {
    let raw_header = "";
    for (let line of lines) {
      if (/^# data_set/.test(line)) {
        break
      }
      raw_header += line.replace(/^# /, '') + '\n';
    }
    let header = yaml_load(raw_header);
    return header?.reduction?.software?.template_data;
  }
}

export function reload(contents) {
  let content_type = get_type(contents);
  if (content_type in readers) {
    return readers[content_type](contents)
  }
}