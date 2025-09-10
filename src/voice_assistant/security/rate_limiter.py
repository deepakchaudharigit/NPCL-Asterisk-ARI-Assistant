"""
Rate Limiting Implementation
Provides various rate limiting strategies for API protection
"""

import time
import asyncio
from typing import Dict, Optional, Any, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections import defaultdict, deque
import redis
import logging

logger = logging.getLogger(__name__)

@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests: int  # Number of requests
    window: int    # Time window in seconds
    burst: int = None  # Burst allowance
    
@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[int] = None

class RateLimiter(ABC):
    """Abstract base class for rate limiters"""
    
    @abstractmethod
    async def is_allowed(self, key: str, limit: RateLimit) -> RateLimitResult:
        """Check if request is allowed under rate limit"""
        pass
    
    @abstractmethod
    async def reset(self, key: str) -> bool:
        """Reset rate limit for key"""
        pass

class TokenBucketRateLimiter(RateLimiter):
    """Token bucket rate limiter implementation"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.local_buckets: Dict[str, Dict[str, Any]] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    async def is_allowed(self, key: str, limit: RateLimit) -> RateLimitResult:
        """Check if request is allowed using token bucket algorithm"""
        if self.redis_client:
            return await self._redis_token_bucket(key, limit)
        else:
            return await self._local_token_bucket(key, limit)
    
    async def _redis_token_bucket(self, key: str, limit: RateLimit) -> RateLimitResult:
        """Redis-based token bucket implementation"""
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local window = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now
        
        -- Calculate tokens to add
        local time_passed = now - last_refill
        local tokens_to_add = math.floor(time_passed * refill_rate)
        tokens = math.min(capacity, tokens + tokens_to_add)
        
        local allowed = tokens >= 1
        if allowed then
            tokens = tokens - 1
        end
        
        -- Update bucket
        redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
        redis.call('EXPIRE', key, window * 2)
        
        return {allowed and 1 or 0, tokens, now + (1 / refill_rate)}
        """
        
        try:
            refill_rate = limit.requests / limit.window
            result = await self.redis_client.eval(
                lua_script, 1, key, 
                limit.requests, refill_rate, limit.window, time.time()
            )
            
            allowed, remaining, reset_time = result
            return RateLimitResult(
                allowed=bool(allowed),
                remaining=int(remaining),
                reset_time=float(reset_time),
                retry_after=int(1 / refill_rate) if not allowed else None
            )
        except Exception as e:
            logger.error(f"Redis rate limiter error: {e}")
            # Fallback to local implementation
            return await self._local_token_bucket(key, limit)
    
    async def _local_token_bucket(self, key: str, limit: RateLimit) -> RateLimitResult:
        """Local memory token bucket implementation"""
        now = time.time()
        
        # Cleanup old buckets periodically
        if now - self.last_cleanup > self.cleanup_interval:
            await self._cleanup_buckets()
            self.last_cleanup = now
        
        if key not in self.local_buckets:
            self.local_buckets[key] = {
                'tokens': limit.requests,
                'last_refill': now,
                'capacity': limit.requests,
                'refill_rate': limit.requests / limit.window
            }
        
        bucket = self.local_buckets[key]
        
        # Calculate tokens to add
        time_passed = now - bucket['last_refill']
        tokens_to_add = time_passed * bucket['refill_rate']
        bucket['tokens'] = min(bucket['capacity'], bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = now
        
        # Check if request is allowed
        allowed = bucket['tokens'] >= 1
        if allowed:
            bucket['tokens'] -= 1
        
        return RateLimitResult(
            allowed=allowed,
            remaining=int(bucket['tokens']),
            reset_time=now + (1 / bucket['refill_rate']),
            retry_after=int(1 / bucket['refill_rate']) if not allowed else None
        )
    
    async def reset(self, key: str) -> bool:
        """Reset rate limit for key"""
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
                return True
            except Exception as e:
                logger.error(f"Redis reset error: {e}")
        
        if key in self.local_buckets:
            del self.local_buckets[key]
            return True
        
        return False
    
    async def _cleanup_buckets(self):
        """Clean up old local buckets"""
        now = time.time()
        expired_keys = []
        
        for key, bucket in self.local_buckets.items():
            if now - bucket['last_refill'] > 3600:  # 1 hour
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.local_buckets[key]

class SlidingWindowRateLimiter(RateLimiter):
    """Sliding window rate limiter implementation"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.local_windows: Dict[str, deque] = defaultdict(deque)
    
    async def is_allowed(self, key: str, limit: RateLimit) -> RateLimitResult:
        """Check if request is allowed using sliding window"""
        if self.redis_client:
            return await self._redis_sliding_window(key, limit)
        else:
            return await self._local_sliding_window(key, limit)
    
    async def _redis_sliding_window(self, key: str, limit: RateLimit) -> RateLimitResult:
        """Redis-based sliding window implementation"""
        lua_script = """
        local key = KEYS[1]
        local window = tonumber(ARGV[1])
        local limit = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local window_start = now - window
        
        -- Remove old entries
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
        
        -- Count current requests
        local current = redis.call('ZCARD', key)
        
        local allowed = current < limit
        if allowed then
            -- Add current request
            redis.call('ZADD', key, now, now)
            current = current + 1
        end
        
        -- Set expiration
        redis.call('EXPIRE', key, window)
        
        return {allowed and 1 or 0, limit - current, now + window}
        """
        
        try:
            result = await self.redis_client.eval(
                lua_script, 1, key,
                limit.window, limit.requests, time.time()
            )
            
            allowed, remaining, reset_time = result
            return RateLimitResult(
                allowed=bool(allowed),
                remaining=max(0, int(remaining)),
                reset_time=float(reset_time),
                retry_after=limit.window if not allowed else None
            )
        except Exception as e:
            logger.error(f"Redis sliding window error: {e}")
            return await self._local_sliding_window(key, limit)
    
    async def _local_sliding_window(self, key: str, limit: RateLimit) -> RateLimitResult:
        """Local memory sliding window implementation"""
        now = time.time()
        window_start = now - limit.window
        
        # Get or create window for key
        window = self.local_windows[key]
        
        # Remove old entries
        while window and window[0] <= window_start:
            window.popleft()
        
        # Check if request is allowed
        allowed = len(window) < limit.requests
        if allowed:
            window.append(now)
        
        remaining = max(0, limit.requests - len(window))
        reset_time = window[0] + limit.window if window else now
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=limit.window if not allowed else None
        )
    
    async def reset(self, key: str) -> bool:
        """Reset rate limit for key"""
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
                return True
            except Exception as e:
                logger.error(f"Redis reset error: {e}")
        
        if key in self.local_windows:
            self.local_windows[key].clear()
            return True
        
        return False

class AdaptiveRateLimiter(RateLimiter):
    """Adaptive rate limiter that adjusts based on system load"""
    
    def __init__(self, base_limiter: RateLimiter):
        self.base_limiter = base_limiter
        self.system_load = 0.0
        self.error_rate = 0.0
        self.last_adjustment = time.time()
    
    async def is_allowed(self, key: str, limit: RateLimit) -> RateLimitResult:
        """Check if request is allowed with adaptive limits"""
        # Adjust limit based on system conditions
        adjusted_limit = self._adjust_limit(limit)
        return await self.base_limiter.is_allowed(key, adjusted_limit)
    
    def _adjust_limit(self, limit: RateLimit) -> RateLimit:
        """Adjust rate limit based on system conditions"""
        # Reduce limit if system is under stress
        adjustment_factor = 1.0
        
        if self.system_load > 0.8:
            adjustment_factor *= 0.5  # Reduce by 50%
        elif self.system_load > 0.6:
            adjustment_factor *= 0.7  # Reduce by 30%
        
        if self.error_rate > 0.1:  # 10% error rate
            adjustment_factor *= 0.6  # Reduce by 40%
        
        adjusted_requests = max(1, int(limit.requests * adjustment_factor))
        
        return RateLimit(
            requests=adjusted_requests,
            window=limit.window,
            burst=limit.burst
        )
    
    async def update_system_metrics(self, cpu_usage: float, error_rate: float):
        """Update system metrics for adaptive adjustment"""
        self.system_load = cpu_usage
        self.error_rate = error_rate
        self.last_adjustment = time.time()
    
    async def reset(self, key: str) -> bool:
        """Reset rate limit for key"""
        return await self.base_limiter.reset(key)

class RateLimitMiddleware:
    """Middleware for applying rate limits to requests"""
    
    def __init__(self, rate_limiter: RateLimiter, 
                 default_limits: Dict[str, RateLimit] = None):
        self.rate_limiter = rate_limiter
        self.default_limits = default_limits or {}
        self.custom_limits: Dict[str, RateLimit] = {}
    
    async def check_rate_limit(self, identifier: str, 
                              endpoint: str = "default") -> RateLimitResult:
        """Check rate limit for identifier and endpoint"""
        # Get rate limit for endpoint
        limit = self.custom_limits.get(endpoint) or \
                self.default_limits.get(endpoint) or \
                RateLimit(requests=100, window=3600)  # Default: 100/hour
        
        # Create key combining identifier and endpoint
        key = f"rate_limit:{identifier}:{endpoint}"
        
        return await self.rate_limiter.is_allowed(key, limit)
    
    def set_custom_limit(self, endpoint: str, limit: RateLimit):
        """Set custom rate limit for endpoint"""
        self.custom_limits[endpoint] = limit
    
    def get_rate_limit_headers(self, result: RateLimitResult) -> Dict[str, str]:
        """Get HTTP headers for rate limit information"""
        headers = {
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(int(result.reset_time))
        }
        
        if result.retry_after:
            headers["Retry-After"] = str(result.retry_after)
        
        return headers