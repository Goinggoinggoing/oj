import time


class TokenBucketWithLua(object):
    def __init__(self, capacity, fill_rate, redis_conn):
        self._capacity = float(capacity)
        self._fill_rate = float(fill_rate)
        self._redis_conn = redis_conn
        self._script = """
            local tokens_key = KEYS[1]
            local timestamp_key = KEYS[2]
            local capacity = tonumber(ARGV[1])
            local fill_rate = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            -- now = redis.call("time")
            -- now = tonumber(now[1]) + tonumber(now[2]) / 1000000
            
            local tokens = tonumber(redis.call("get", tokens_key))
            if tokens == nil then
                tokens = capacity
            end
            local timestamp = tonumber(redis.call("get", timestamp_key))
            if timestamp == nil then
                timestamp = now
            end
            local delta = math.max(0, now - timestamp) * fill_rate
            local rate_limited = false
            tokens = tokens + delta
            if tokens > capacity then
                tokens = capacity
            end
            if tokens < 1 then
                rate_limited = true
            else
                tokens = tokens - 1
                redis.call("set", tokens_key, tokens)
                redis.call("set", timestamp_key, now)
            end

            return rate_limited
        """

    def can_consume(self):
        keys = ['tokens', 'timestamp']
        args = [self._capacity, self._fill_rate, time.time()]
        rate_limited = self._redis_conn.eval(self._script, len(keys), *keys, *args)
        return not rate_limited