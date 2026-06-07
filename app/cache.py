"""
In-memory cache implementation for storing API responses with a time-to-live (TTL) mechanism. This cache allows for quick retrieval of previously fetched responses, reducing the need for repeated API calls and improving performance. The cache uses a simple dictionary to store responses, with the URL as the key and a timestamp to manage expiration.
"""

import hashlib
import time
from typing import Optional

class ResponseCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._cache: dict[str, dict] = {}
        self._hits = 0
        self._misses = 0

    def _make_cache_key(self, query: str) -> str:
        normalized_query = query.strip().lower()
        return hashlib.sha256(normalized_query.encode()).hexdigest()

    # 'What is Python ? and what is python ?' should map to the same cache key

    def get(self, query: str) -> Optional[str]:
        key = self._make_cache_key(query)
        
        if key in self._cache:
            entry = self._cache[key]
            # Check TTL
            if time.time() - entry["timestamp"] < self.ttl:
                self._hits += 1
                return entry["response"]
            else:
                del self._cache[key]  # Expired entry
        
        self._misses += 1
        return None

    def set(self, query: str, response: str) -> None:
        key = self._make_cache_key(query)
        self._cache[key] = {
            "response": response,
            "timestamp": time.time(),
            "query": query
        }
    
    @property
    def stats(self) -> dict:
        
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1%}",
            "cached_entries": len(self._cache),
        }

def demo_cache():
    cache = ResponseCache(ttl_seconds=3)

    print("=== Cache Demo ===")
    print()
    
    # First query (miss)
    result = cache.get("What is Python?")
    print(f'Query: "What is Python?" - Cache Miss: {result}')

    # Store response in cache
    cache.set("What is Python?", "Python is a programming language.")
    print(f'Stored response for "What is Python?"')

    # Retrieve from cache (hit)
    result = cache.get("What is Python?")
    print(f'Retrieved response for "What is Python?": {result}')

    # Case sensitive query (should hit due to normalization)
    result = cache.get("what is python?")
    print(f'Query: "what is python?" - Cache Hit: {result}')

    # Different query (miss)
    result = cache.get("What is Java?")
    print(f'Query: "What is Java?" - Cache Miss: {result}')

    # state of cache
    print("\nCache Stats:", cache.stats)

    # Wait for TTL to expire
    print("\nWaiting for TTL to expire...")
    time.sleep(4)
    result = cache.get("What is Python?")
    print(f'Query: "What is Python?" after TTL - Cache Miss: {result}')
    print("\nCache Stats after TTL expiration:", cache.stats)


if __name__ == "__main__":
    demo_cache()

