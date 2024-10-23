#!/usr/bin/env python3
'''
A module providing tools for caching HTTP
requests and tracking request counts.
'''
import redis
import requests
from functools import wraps
from typing import Callable


redis_store = redis.Redis()
'''A Redis instance used for caching and tracking request data.
'''


def data_cacher(method: Callable) -> Callable:
    '''
    Decorator that caches the result of
    a URL fetch and tracks the number of requests.
    '''
    @wraps(method)
    def invoker(url) -> str:
        '''
        Wrapper function that increments
        the request counter, checks for cached data,
        and fetches new data if not already cached.
        '''
        redis_store.incr(f'count:{url}')
        cached_result = redis_store.get(f'result:{url}')
        if cached_result:
            return cached_result.decode('utf-8')
        result = method(url)
        redis_store.set(f'count:{url}', 0)
        redis_store.setex(f'result:{url}', 10, result)
    return invoker


@data_cacher
def get_page(url: str) -> str:
    '''
    Fetches the content of a given URL,
    caching the result and tracking the number of requests.
    '''
    return requests.get(url).text
