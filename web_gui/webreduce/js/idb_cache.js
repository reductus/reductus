import { idb } from './libraries.js';

export class Cache {
  constructor(dbname = 'calculations', storename = 'calculations') {
    this.dbname = dbname;
    this.storename = storename;
    this.dbPromise = idb.openDB(dbname, 1, {
      upgrade(db) {
        // Create a store of objects
        const store = db.createObjectStore(storename, {
          // The 'id' property of the object will be the key.
          keyPath: '_id',
          // If it isn't explicitly set, create a value by auto incrementing.
          autoIncrement: false,
        });
        // Create an index on the 'date' property of the objects.
        store.createIndex('created_at', 'created_at', { unique: false });
      },
    });
  }

  async get_newer_than(timestamp) {
    let keyRangeValue = IDBKeyRange.lowerBound(timestamp);
    let cursor = await (await this.dbPromise).transaction(this.storename, 'readonly').store.index('created_at').openCursor(keyRangeValue);
    let output = [];
    while (cursor) {
      output.push(cursor.value);
      cursor = await cursor.continue();
    }
    console.log('done');
    return output
  }

  async remove_older(timestamp) {
    // remove all items with created_at < timestamp
    let keyRangeValue = IDBKeyRange.upperBound(timestamp);
    let cursor = await (await this.dbPromise).transaction(this.storename, 'readwrite').store.index('created_at').openCursor(keyRangeValue);
    while (cursor) {
      // let 'delete' run in another thread, or await?
      cursor.delete();
      cursor = await cursor.continue();
    }
  }

  async get(key) {
    return (await this.dbPromise).get(this.storename, key);
  }

  async set(key, val) {
    return (await this.dbPromise).put(this.storename, val);
  }

  async del(key) {
    return (await this.dbPromise).delete(this.storename, key);
  }

  async clear() {
    return (await this.dbPromise).clear(this.storename);
  }

  async keys() {
    return (await this.dbPromise).getAllKeys(this.storename);
  }

  async count() {
    return (await this.dbPromise).count(this.storename);
  }
}


