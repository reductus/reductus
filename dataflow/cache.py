"""
Calculations can be cached, either using a redis server or using a local
in-memory cache.  The redis server is useful when serving calculations
over the net via CGI since it can be used by different processes.

A singleton :class:`CacheManager` is available for programs that only
need a single shared cache.  Call *cache.use_redis(redis args)* during
program configuration to set up redis, otherwise the default is to use
an in-memory cache.   The calculation library will call *cache.get_cache()*
to retrieve the cache connection, allowing calculations to be memoized.
"""
import warnings
import sys
import os
import subprocess
import time
import tempfile

try:
    # CRUFT: use cPickle for python 2.7
    import cPickle as pickle
except ImportError:
    import pickle

PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL # use the best

def memory_cache():
    from . import fakeredis
    return fakeredis.MemoryCache()

def file_cache(cachedir="~/.reductus/cache"):
    from . import fakeredis
    return fakeredis.FileBasedCache(cachedir=cachedir)


# port 6379 is the default port value for the python redis connection
def redis_connect(host="localhost", port=6379, maxmemory=4.0, **kwargs):
    """
    Open a redis connection.

    If host is localhost, then try starting the redis server.

    If redis is unavailable, then return a simple dict cache.
    """
    import redis  # lazy import so that redis need not be available

    # ensure redis is running, at least if we are not on a windows box
    try:
        cache = redis.Redis(host=host, port=port, **kwargs)
        # first, check to see if it is already running:
        cache.ping()
    except redis.exceptions.ConnectionError:
        # if it's not running, and this is a platform on which we can start it:
        if host == "localhost" and not sys.platform == 'win32':
            subprocess.Popen(["redis-server"],
                             stdout=open(os.devnull, "w"),
                             stderr=subprocess.STDOUT)
            time.sleep(10)
            cache = redis.Redis(host=host, port=port, **kwargs)
            cache.ping()
        else:
            raise

    # set the memory settings for already-running Redis:
    cache.config_set("maxmemory", "%d" % (int(maxmemory*2**30),))
    cache.config_set("maxmemory-policy", "allkeys-lru")

    return cache

class CacheManager(object):
    """
    Manage the connection to the key-value cache.
    """
    def __init__(self):
        self._cache = None
        self._file_cache = None
        self._engine = None
        self._use_compression = False
        self._pickle_protocol = PICKLE_PROTOCOL

    @property
    def engine(self):
        return self._engine

    def use_memory(self):
        """
        Set up cache for testing.
        """
        if self._cache is None:
            cachedir = os.path.join(tempfile.gettempdir(), "reductus_test")
            self._cache = memory_cache()
            self._file_cache = file_cache(cachedir=cachedir)
            self._cache_engine = "memory"

    def use_diskcache(self, **kwargs):
        """
        use the PyPi package 'diskcache' as the main store
        """
        try:
            from diskcache import FanoutCache as Cache
            # patch the class so it has "exists" method
            Cache.exists = Cache.__contains__
            cachedir = kwargs.pop("cachedir", "cache")
            self._cache = Cache(cachedir, **kwargs)
            file_cachedir = kwargs.pop("file_cachedir", "files_cache")
            self._file_cache = Cache(file_cachedir, **kwargs)
            self._cache_engine = "diskcache"
            return
        except Exception as exc:
            warning = "diskcache connection failed with:\n\t" + str(exc)
            warning += "\nFalling back to in-memory cache."
            warnings.warn(warning)
            self.use_memory()
        

    def use_redis(self, **kwargs):
        """
        Use redis for managing the cache.

        The arguments given to use_redis will be used to connect to the
        redis server when get_cache() is called.   See *redis.Redis()* for
        details.  If use_redis() is not called, then get_cache() will use
        an in-memory cache instead.
        """
        try:
            self._cache = redis_connect(**kwargs)
            self._file_cache = self._cache
            self._cache_engine = "redis"
            return
        except Exception as exc:
            warning = "Redis connection failed with:\n\t" + str(exc)
            warning += "\nFalling back to in-memory cache."
            warnings.warn(warning)
            self.use_memory()

    def get_cache(self):
        """
        Connect to the key-value cache.
        """
        if self._cache is None:
            self.use_memory()
        return self._cache

    def get_cache_manager(self):
        """
        return this manager class
        """
        if self._cache is None:
            self.use_memory()
        return self

    def get_file_cache(self):
        """
        Connect to the file cache.
        """
        if self._cache is None:
            self.use_memory()
        return self._file_cache

    def store_file(self, key, contents):
        if self._use_compression:
            import lz4.frame
            contents = lz4.frame.compress(contents)
        self._file_cache.set(key, contents)

    def retrieve_file(self, key):
        contents = self._file_cache.get(key)
        if self._use_compression:
            import lz4.frame
            contents = lz4.frame.decompress(contents)
        return contents

    def store(self, key, value):
        string = pickle.dumps(value, protocol=self._pickle_protocol)
        if self._use_compression:
            import lz4.frame
            string = lz4.frame.compress(string)
        self._cache.set(key, string)

    def retrieve(self, key):
        string = self._cache.get(key)
        if self._use_compression:
            import lz4.frame
            string = lz4.frame.decompress(string)
        value = pickle.loads(string)
        return value

    def delete(self, key):
        self._cache.delete(key)

    def file_exists(self, key):
        return self._file_cache.exists(key)
        
    def exists(self, key):
        return self._cache.exists(key)


# Singleton cache manager if you only need one cache
CACHE_MANAGER = CacheManager()

# direct access to singleton methods
use_redis = CACHE_MANAGER.use_redis
use_diskcache = CACHE_MANAGER.use_diskcache
get_cache = CACHE_MANAGER.get_cache_manager
get_file_cache = CACHE_MANAGER.get_file_cache
set_test_cache = CACHE_MANAGER.use_memory
