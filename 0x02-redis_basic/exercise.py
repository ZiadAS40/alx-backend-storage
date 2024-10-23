#!/usr/bin/env python3
'''A module for interacting with Redis NoSQL data storage.
'''
from functools import wraps
from typing import Any, Callable, Union
import redis
import uuid


def track_calls(method: Callable) -> Callable:
    '''Increments the call count of a method in the Cache class.
    '''
    @wraps(method)
    def wrapper(self, *args, **kwargs) -> Any:
        '''Increments the counter for the method and returns its result.
        '''
        if isinstance(self._redis_instance, redis.Redis):
            self._redis_instance.incr(method.__qualname__)
        return method(self, *args, **kwargs)

    return wrapper


def record_history(method: Callable) -> Callable:
    '''Logs the input and output of a method in the Cache class.
    '''
    @wraps(method)
    def recorder(self, *args, **kwargs) -> Any:
        '''Records the arguments and results, then executes the method.
        '''
        input_key = f'{method.__qualname__}:args'
        output_key = f'{method.__qualname__}:results'
        if isinstance(self._redis_instance, redis.Redis):
            self._redis_instance.rpush(input_key, str(args))
        result = method(self, *args, **kwargs)
        if isinstance(self._redis_instance, redis.Redis):
            self._redis_instance.rpush(output_key, result)
        return result
    return recorder


def display_history(fn: Callable) -> None:
    '''Shows the call history for a method in the Cache class.
    '''
    if not fn or not hasattr(fn, '__self__'):
        return
    redis_conn = getattr(fn.__self__, '_redis_instance', None)
    if not isinstance(redis_conn, redis.Redis):
        return
    method_name = fn.__qualname__
    input_key = f'{method_name}:args'
    output_key = f'{method_name}:results'
    call_count = 0
    if redis_conn.exists(method_name):
        call_count = int(redis_conn.get(method_name))
    print(f'{method_name} was called {call_count} times:')

    inputs = redis_conn.lrange(input_key, 0, -1)
    outputs = redis_conn.lrange(output_key, 0, -1)

    for args, result in zip(inputs, outputs):
        print(f'{method_name}(*{args.decode("utf-8")}) -> {result}')


class Cache:
    '''Handles storing and retrieving data in Redis.
    '''

    def __init__(self) -> None:
        self._redis_instance = redis.Redis()
        self._redis_instance.flushdb(asynchronous=True)

    @record_history
    @track_calls
    def store(self, data: Union[str, bytes, int, float]) -> str:
        '''Saves a value to Redis and returns the generated key.
        '''
        key = str(uuid.uuid4())
        self._redis_instance.set(key, data)
        return key

    def get(
            self,
            key: str,
            transform_fn: Callable = None,
            ) -> Union[str, bytes, int, float]:
        '''Fetches a value from Redis and optionally transforms it.
        '''
        value = self._redis_instance.get(key)
        return transform_fn(value) if transform_fn else value

    def get_str(self, key: str) -> str:
        '''Fetches and decodes a string value from Redis.
        '''
        return self.get(key, lambda val: val.decode('utf-8'))

    def get_int(self, key: str) -> int:
        '''Fetches and converts a value from Redis into an integer.
        '''
        return self.get(key, lambda val: int(val))
