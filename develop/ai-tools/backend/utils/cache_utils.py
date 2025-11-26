

import os
import time
import json
import pickle
import logging
import threading
from typing import Dict, Any, Optional, Callable, Tuple, TypeVar, Generic, List, Union
from functools import wraps
from datetime import datetime, timedelta

# Type variables for generic caching
K = TypeVar('K')  # Key type
V = TypeVar('V')  # Value type

# Configure logger
logger = logging.getLogger("CacheUtils")

# Default cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")

class MemoryCache(Generic[K, V]):
    """
    Thread-safe in-memory cache with TTL support.
    
    Attributes:
        max_size: Maximum number of items in the cache
        ttl: Default time-to-live in seconds
        statistics: Cache statistics (hits, misses, evictions)
    """
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of items in the cache
            ttl: Default time-to-live in seconds (0 means no expiration)
        """
        self.max_size = max_size
        self.default_ttl = ttl
        self._cache: Dict[K, Tuple[V, float]] = {}  # (value, expiration_timestamp)
        self._lock = threading.RLock()
        self.statistics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "insertions": 0,
            "size": 0,
        }
        
    def put(self, key: K, value: V, ttl: Optional[int] = None) -> None:
        """
        Add or update an item in the cache.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (None uses default, 0 means no expiration)
        """
        with self._lock:
            # Check if we need to evict items
            self._cleanup_expired()
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_oldest()
                
            # Calculate expiration time
            expiration = time.time() + (ttl if ttl is not None else self.default_ttl) if (ttl != 0) else float('inf')
            
            # Add to cache
            self._cache[key] = (value, expiration)
            
            # Update statistics
            if key in self._cache:
                self.statistics["insertions"] += 1
            self.statistics["size"] = len(self._cache)
            
    def get(self, key: K) -> Optional[V]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            The cached value or None if not found or expired
        """
        with self._lock:
            if key in self._cache:
                value, expiration = self._cache[key]
                if expiration > time.time():
                    # Valid cache hit
                    self.statistics["hits"] += 1
                    return value
                else:
                    # Expired
                    del self._cache[key]
                    self.statistics["size"] = len(self._cache)
                    
            self.statistics["misses"] += 1
            return None
            
    def contains(self, key: K) -> bool:
        """
        Check if a key exists in the cache and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key exists and is not expired, False otherwise
        """
        with self._lock:
            if key in self._cache:
                _, expiration = self._cache[key]
                return expiration > time.time()
            return False
            
    def remove(self, key: K) -> bool:
        """
        Remove a key from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key was removed, False if it didn't exist
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.statistics["size"] = len(self._cache)
                return True
            return False
            
    def clear(self) -> None:
        """Clear all items from the cache."""
        with self._lock:
            self._cache.clear()
            self.statistics["size"] = 0
            
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            return self.statistics.copy()
            
    def _cleanup_expired(self) -> int:
        """
        Remove expired items from the cache.
        
        Returns:
            Number of items removed
        """
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._cache.items() if exp <= now]
        
        for key in expired_keys:
            del self._cache[key]
            
        self.statistics["evictions"] += len(expired_keys)
        self.statistics["size"] = len(self._cache)
        return len(expired_keys)
            
    def _evict_oldest(self) -> None:
        """Evict the oldest item from the cache."""
        if not self._cache:
            return
            
        # Find the item with the lowest expiration time (oldest)
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
        del self._cache[oldest_key]
        self.statistics["evictions"] += 1
        self.statistics["size"] = len(self._cache)

class DiskCache:
    """
    Persistent disk-based cache with TTL support.
    
    Attributes:
        cache_dir: Directory for cache files
        ttl: Default time-to-live in seconds
    """
    def __init__(self, cache_dir: Optional[str] = None, ttl: int = 86400, 
                 max_size_mb: int = 100):
        """
        Initialize the disk cache.
        
        Args:
            cache_dir: Directory for cache files (None uses default)
            ttl: Default time-to-live in seconds (0 means no expiration)
            max_size_mb: Maximum cache size in megabytes
        """
        self.cache_dir = cache_dir or CACHE_DIR
        self.default_ttl = ttl
        self.max_size_mb = max_size_mb
        self._lock = threading.RLock()
        self._ensure_cache_dir()
        
    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
            except Exception as e:
                logger.error(f"Failed to create cache directory {self.cache_dir}: {e}")
                
    def _get_cache_path(self, key: str) -> str:
        """
        Get the file path for a cache key.
        
        Args:
            key: Cache key
            
        Returns:
            File path for the cache item
        """
        # Use a safe filename
        safe_key = "".join(c if c.isalnum() else "_" for c in str(key))
        return os.path.join(self.cache_dir, f"{safe_key}.cache")
        
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Add or update an item in the cache.
        
        Args:
            key: Cache key
            value: Value to store (must be JSON serializable or picklable)
            ttl: Time-to-live in seconds (None uses default, 0 means no expiration)
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                cache_path = self._get_cache_path(key)
                
                # Calculate expiration time
                expiration = time.time() + (ttl if ttl is not None else self.default_ttl) if (ttl != 0) else float('inf')
                
                # Check cache size before writing
                self._cleanup_cache()
                
                # Create cache entry
                cache_entry = {
                    "key": key,
                    "expiration": expiration,
                    "timestamp": time.time(),
                    "value": value
                }
                
                # Write to file
                with open(cache_path, 'wb') as f:
                    pickle.dump(cache_entry, f)
                    
                return True
            except Exception as e:
                logger.error(f"Error saving to cache for key {key}: {e}")
                return False
                
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            The cached value or None if not found or expired
        """
        with self._lock:
            try:
                cache_path = self._get_cache_path(key)
                
                if not os.path.exists(cache_path):
                    return None
                    
                # Read cache entry
                with open(cache_path, 'rb') as f:
                    cache_entry = pickle.load(f)
                    
                # Check expiration
                if cache_entry.get("expiration", 0) > time.time():
                    return cache_entry.get("value")
                else:
                    # Expired - remove the file
                    try:
                        os.remove(cache_path)
                    except:
                        pass
                    return None
            except Exception as e:
                logger.error(f"Error reading from cache for key {key}: {e}")
                return None
                
    def contains(self, key: str) -> bool:
        """
        Check if a key exists in the cache and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key exists and is not expired, False otherwise
        """
        return self.get(key) is not None
            
    def remove(self, key: str) -> bool:
        """
        Remove a key from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key was removed, False if it didn't exist
        """
        with self._lock:
            try:
                cache_path = self._get_cache_path(key)
                
                if not os.path.exists(cache_path):
                    return False
                    
                os.remove(cache_path)
                return True
            except Exception as e:
                logger.error(f"Error removing from cache for key {key}: {e}")
                return False
                
    def clear(self) -> int:
        """
        Clear all items from the cache.
        
        Returns:
            Number of items removed
        """
        with self._lock:
            count = 0
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".cache"):
                    try:
                        os.remove(os.path.join(self.cache_dir, filename))
                        count += 1
                    except Exception as e:
                        logger.error(f"Error removing cache file {filename}: {e}")
            return count
            
    def _cleanup_cache(self) -> int:
        """
        Clean up the cache by removing expired items and
        ensuring the cache size is below the maximum.
        
        Returns:
            Number of items removed
        """
        now = time.time()
        removed = 0
        
        # First, remove expired items
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith(".cache"):
                continue
                
            filepath = os.path.join(self.cache_dir, filename)
            try:
                with open(filepath, 'rb') as f:
                    cache_entry = pickle.load(f)
                    
                if cache_entry.get("expiration", 0) <= now:
                    os.remove(filepath)
                    removed += 1
            except Exception:
                # If we can't read it, remove it
                try:
                    os.remove(filepath)
                    removed += 1
                except:
                    pass
        
        # Check total cache size
        total_size_mb = sum(os.path.getsize(os.path.join(self.cache_dir, f)) 
                          for f in os.listdir(self.cache_dir) 
                          if f.endswith(".cache")) / (1024 * 1024)
                          
        if total_size_mb > self.max_size_mb:
            # Get files sorted by modification time (oldest first)
            files = [(f, os.path.getmtime(os.path.join(self.cache_dir, f))) 
                    for f in os.listdir(self.cache_dir) 
                    if f.endswith(".cache")]
            files.sort(key=lambda x: x[1])
            
            # Remove oldest files until we're under the limit
            for filename, _ in files:
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    os.remove(filepath)
                    removed += 1
                    total_size_mb -= file_size_mb
                    
                    if total_size_mb <= self.max_size_mb * 0.9:  # 90% of limit
                        break
                except Exception:
                    pass
                    
        return removed

def memoize(ttl: int = 3600):
    """
    Decorator for memoizing function results.
    
    Args:
        ttl: Time-to-live in seconds (0 means no expiration)
        
    Returns:
        Decorated function
    """
    cache = MemoryCache(ttl=ttl)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a key from the function name and arguments
            key = str((func.__name__, args, tuple(sorted(kwargs.items()))))
            
            # Check cache
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result
                
            # Call the function and cache the result
            result = func(*args, **kwargs)
            cache.put(key, result)
            return result
            
        return wrapper
        
    return decorator
