import warnings

def lrucache(size):
    try:
        import pylru
        return pylru.lrucache(size)
    except ImportError:
        warnings.warn("pylru not available; using simple cache with no size limit")
        return {}


class MemoryCache:
    """
    In memory cache with redis interface.

    Use this for running tests without having to start up the redis server.
    """
    def __init__(self, size=1000):
        self.cache = lrucache(size)
    def exists(self, key):
        return key in self.cache
    def keys(self):
        return self.cache.keys()
    def delete(self, *key):
        for k in key:
            del self.cache[k]
    def set(self, key, value):
        self.cache[key] = value
    def get(self, key):
        """Note: doesn't provide default value for missing key like dict.get"""
        return self.cache[key]
    __delitem__ = delete
    __setitem__ = set
    __getitem__ = get
    def rpush(self, key, value):
        if key not in self.cache:
            self.cache[key] = [value]
        else:
            self.cache[key].append(value)
    def lrange(self, key, low, high):
        return self.cache[key][low:high]


def demo():
    class Expensive(object):
        def __del__(self):
            print '(Deleting %d)'% self.a
        def __init__(self, a):
            self.a = a
            print '(Creating %s)'% self.a
    print "test using get/set interface"
    cache = MemoryCache(5)
    for k in range(5):
        print "=== inserting %d"%k
        cache.set(k, Expensive(k))
    for k in range(5):
        print "=== inserting %d, deleting %d"%(k+5,k)
        cache.set(k+5, Expensive(k+5))
    print "=== accessing oldest element, 5"
    a = cache.get(5)
    print "=== inserting 10 and deleting 6"
    cache.set(10, Expensive(10))

    print
    print "test using dict-like interface"
    cache2 = MemoryCache(5)
    for k in range(5):
        print "=== inserting %d"%k
        cache2[k] = Expensive(k)
    for k in range(5):
        print "=== inserting %d, deleting %d"%(k+5,k)
        cache2[k+5] = Expensive(k+5)
    print "=== accessing oldest element, 5"
    a = cache2[5]
    print "=== inserting 10 and deleting 6"
    cache2[10] = Expensive(10)
    
    print "=== cleanup can happen in any order"

if __name__ == "__main__":
    demo()    
     
