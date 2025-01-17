
/**
 * Add a link to the web viewer for each entry (leaf) in the tree
 * @param {treeNode[]} node_list 
 * @param {treeNode[]} leaf_list 
 * @param {Object.<string, treeNode>} node_parents 
 * @param {object} file_objs 
 */
export function add_viewer_link(node_list, leaf_list, node_parents, file_objs) {
  const viewer_link = {
    "ncnr": "https://ncnr.nist.gov/ncnrdata/view/nexus-zip-viewer.html",
    "ncnr_DOI": "https://ncnr.nist.gov/ncnrdata/view/nexus-zip-viewer.html",
    "charlotte": "https://charlotte.ncnr.nist.gov/ncnrdata/view/nexus-zip-viewer.html"
  }
  let NEXUZ_REGEXP = /\.nxz\.[^\.\/]+$/
  let NEXUS_REGEXP = /\.nxs\.[^\.\/]+(\.zip)?$/
  let decorated = new Set();

  for (let leaf of leaf_list) {
    let fileinfo = leaf.metadata.fileinfo;
    let datasource = fileinfo.source;
    let fullpath = fileinfo.filename;
    if (!(NEXUS_REGEXP.test(fullpath) || NEXUZ_REGEXP.test(fullpath))) {
      continue
    }
    if (viewer_link[datasource]) {
      if (datasource == "ncnr_DOI") { fullpath = "ncnrdata" + fullpath; }
      let pathsegments = fullpath.split("/");
      let pathlist = pathsegments.slice(0, pathsegments.length - 1).join("+");
      let filename = pathsegments.slice(-1);
      let viewer = viewer_link[datasource];
      let hdf_or_zip = (NEXUS_REGEXP.test(fullpath) ? viewer.replace("-zip-", "-hdf-") : viewer);
      let href = `${hdf_or_zip}?pathlist=${pathlist}&filename=${filename}`;
      let link = `<a href="${href}" target="_blank"><img style="height:1em;width:1em;" src="img/info_symbol.svg"/></a>`;
      leaf.text += link;
      if (leaf.id in node_parents) {
        let parent = node_parents[leaf.id];
        if (!(decorated.has(parent.id)) &&
          parent.children.every(c => (c.metadata.fileinfo.filename == fullpath))
        ) {
          // then all children are entries of the same file, so decorate the parent too.
          parent.text += link;
          decorated.add(parent.id);
        }
      }
    }
  }
}

/**
 * Add a sample description on hover (to element title)
 * @param {treeNode[]} node_list 
 * @param {treeNode[]} leaf_list 
 * @param {Object.<string, treeNode>} node_parents 
 * @param {object} file_objs 
 */
export function add_sample_description(node_list, leaf_list, node_parents, file_objs) {
  for (let leaf of leaf_list) {
    let fileinfo = leaf.metadata.fileinfo;
    let filename = fileinfo.filename;
    let file_obj = file_objs[filename];
    var entry = file_obj.values.filter(function (f) { return f.entry == fileinfo.entryname });
    if (entry && entry[0]) {
      var e = entry[0];
      if ('sample' in e && 'description' in e.sample) {
        leaf.attributes.title = e.sample.description;
        if (leaf.id in node_parents) {
          let parent = node_parents[leaf.id];
          parent.attributes.title = e.sample.description;
        }
      }
    }
  }
}

/**
 * Add counts info on hover (to element title)
 * @param {treeNode[]} node_list 
 * @param {treeNode[]} leaf_list 
 * @param {Object.<string, treeNode>} node_parents 
 * @param {object} file_objs 
 */
export function add_counts(node_list, leaf_list, node_parents, file_objs) {
  for (let leaf of leaf_list) {
    let fileinfo = leaf.metadata.fileinfo;
    let filename = fileinfo.filename;
    let file_obj = file_objs[filename];
    var entry = file_obj.values.filter(function (f) { return f.entry == fileinfo.entryname });
    if (entry && entry[0]) {
      var e = entry[0];
      //console.log(e, ('run.detcnt' in e && 'run.moncnt' in e && 'run.rtime' in e));
      if ('run.detcnt' in e && 'run.moncnt' in e && 'run.rtime' in e) {
        leaf.attributes.title = 't:' + e['run.rtime'] + ' det:' + e['run.detcnt'] + ' mon:' + e['run.moncnt'];
      }
    }
  }
}