"""
Cache manager
=============

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

def memory_cache():
    import fakeredis
    return fakeredis.MemoryCache()
    
def file_cache():
    import fakeredis
    return fakeredis.FileBasedCache()

# port 6379 is the default port value for the python redis connection
def redis_connect(host="localhost", port=6379, maxmemory=4.0, **kwargs):
    """
    Open a redis connection.

    If host is localhost, then try starting the redis server.

    If redis is unavailable, then return a simple dict cache.
    """
    import redis  # lazy import so that redis need not be available

    # ensure redis is running, at least if we are not on a windows box
    redis_connected = False
    try:
        cache = redis.Redis(host=host, port=port, **kwargs)
        # first, check to see if it is already running:
        cache.ping()
        redis_connected = True
    except redis.exceptions.ConnectionError:
        # if it's not running, and this is a platform on which we can start it:
        if host == "localhost" and not sys.platform=='win32':
            subprocess.Popen(["redis-server"], stdout=open(os.devnull, "w"), stderr=subprocess.STDOUT)
            time.sleep(10)
            cache = redis.Redis(host=host, port=port, **kwargs)
            try:
                cache.ping()
                redis_connected = True
            except redis.exceptions.ConnectionError as exc: 
                # if it's still not running, bail out and run the memory cache
                warning = "Redis connection failed with:\n\t"
                warning += str(exc)
                warning += "\nFalling back to in-memory cache."
                warnings.warn(warning)
                cache = memory_cache()
    
    if redis_connected:
        # set the memory settings for already-running Redis:
        cache.config_set("maxmemory", "%d" % (int(maxmemory*2**30),))
        cache.config_set("maxmemory-policy", "allkeys-lru")

    return cache

class CacheManager:
    """
    Manage the connection to the key-value cache.
    """
    def __init__(self):
        self._cache = None
        self._redis_kwargs = None
    def use_redis(self, **kwargs):
        """
        Use redis for managing the cache.

        The arguments given to use_redis will be used to connect to the
        redis server when get_cache() is called.   See *redis.Redis()* for
        details.  If use_redis() is not called, then get_cache() will use
        an in-memory cache instead.
        """
        if self._cache is not None:
            raise RuntimeError("call use_redis() before cache is first used")
        self._redis_kwargs = kwargs
    def get_cache(self):
        """
        Connect to the key-value cache.
        """
        if self._cache is None:
            if self._redis_kwargs is not None:
                self._cache = redis_connect(**self._redis_kwargs)
            else:
                self._cache = memory_cache()
        return self._cache

# Singleton cache manager if you only need one cache
CACHE_MANAGER = CacheManager()

# direct access to singleton methods
use_redis = CACHE_MANAGER.use_redis
get_cache = CACHE_MANAGER.get_cache
