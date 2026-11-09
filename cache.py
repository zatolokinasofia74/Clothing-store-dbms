import redis
import json
import pandas as pd

# Connect to local Redis instance running via Docker
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)


def get_cached_data(key: str):
    """Retrieve data from Redis key as a dictionary or list."""
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
    except redis.RedisError:
        return None
    return None


def set_cached_data(key: str, data: dict | list, ttl_seconds: int = 300):
    """Save serializable data to Redis with a specified time-to-live (TTL)."""
    try:
        redis_client.setex(key, ttl_seconds, json.dumps(data))
    except redis.RedisError:
        pass


def invalidate_cache_key(key: str):
    """Delete a specific key from Redis when data is updated."""
    try:
        redis_client.delete(key)
    except redis.RedisError:
        pass


def clear_all_cache():
    """Flush all stored cache entries."""
    try:
        redis_client.flushdb()
    except redis.RedisError:
        pass