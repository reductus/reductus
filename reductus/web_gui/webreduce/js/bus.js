// Custom async event emitter
function createAsyncEmitter() {
  const handlers = new Map();

  return {
    on(type, handler) {
      if (!handlers.has(type)) {
        handlers.set(type, []);
      }
      handlers.get(type).push(handler);
    },

    off(type, handler) {
      if (!handlers.has(type)) return;
      
      if (handler) {
        const list = handlers.get(type);
        const index = list.indexOf(handler);
        if (index > -1) {
          list.splice(index, 1);
        }
      } else {
        handlers.delete(type);
      }
    },

    async emit(type, data) {
      const list = handlers.get(type);
      if (!list || list.length === 0) return;
      
      // Execute all handlers and wait for them to complete
      await Promise.all(list.map(handler => handler(data)));
    }
  };
}

export const emitter = createAsyncEmitter();