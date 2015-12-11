import warnings
import sys
import os
import pycache


# port 6379 is the default port value for the python redis connection
def redis_connect(host="localhost", port=6379, **kwargs):
    """
    Open a redis connection.

    If host is localhost, then try starting the redis server.

    If redis is unavailable, then return a simple dict cache.
    """
    import redis  # lazy import so that redis need not be available

    # ensure redis is running, at least if we are not on a windows box
    if host == "localhost" and not sys.platform=='win32':
        os.system("nohup redis-server --maxmemory 4gb --maxmemory-policy --port %d allkeys-lru > /dev/null 2>&1 &"
                  % port)

    cache = redis.Redis(host=host, port=port, **kwargs)

    try:
        cache.info()
    except redis.ConnectionError as exc:
        warnings.warn("""\
Redis connection failed with:
    %s
Falling back to in-memory cache."""%str(exc))
        cache = pycache.MemoryCache()

    return cache

class CacheManager:
    def __init__(self):
        self._cache = None
        self._redis_kwargs = None
    def use_redis(self, **kwargs):
        if self._cache is not None:
            raise RuntimeError("call use_redis() before cache is first used")
        self._redis_kwargs = kwargs
    def get_cache(self):
        if self._cache is None:
            if self._redis_kwargs is not None:
                self._cache = redis_connect(**self._redis_kwargs)
            else:
                self._cache = pycache.MemoryCache()
        return self._cache

# Singleton cache manager if you only need one cache
CACHE_MANAGER = CacheManager()

# direct access to singleton methods
use_redis = CACHE_MANAGER.use_redis
get_cache = CACHE_MANAGER.get_cache


