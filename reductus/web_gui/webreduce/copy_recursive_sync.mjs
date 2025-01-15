import fs from 'fs';
import path from 'path';

// This function adapted from https://stackoverflow.com/a/22185855
// with license https://creativecommons.org/licenses/by-sa/4.0/
/**
 * Look ma, it's cp -R.
 * @param {string} src  The path to the thing to copy.
 * @param {string} dest The path to the new copy.
 */
export const copyRecursiveSync = function(src, dest, mode) {
  const exists = fs.existsSync(src);
  const stats = exists && fs.statSync(src);
  const isDirectory = exists && stats.isDirectory();
  if (isDirectory) {
    if (!fs.existsSync(dest)) {
        fs.mkdirSync(dest);
    }
    fs.readdirSync(src).forEach(function(childItemName) {
      copyRecursiveSync(path.join(src, childItemName),
                        path.join(dest, childItemName), mode);
    });
  } else {
    fs.copyFileSync(src, dest, mode);
  }
};