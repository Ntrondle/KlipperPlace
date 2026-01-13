#!/usr/bin/env python3
# State Caching Module for KlipperPlace Middleware
# Provides hardware state caching with TTL support and automatic invalidation

import logging
import asyncio
import time
import re
from typing import Dict, Any, Optional, List, Set, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import aiohttp

# Component logging
logger = logging.getLogger(__name__)


class CacheEntryStatus(Enum):
    """Status of a cache entry."""
    VALID = "valid"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


@dataclass
class CacheEntry:
    """Represents a single cache entry."""
    
    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    ttl: float = 5.0  # Default TTL in seconds
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    status: CacheEntryStatus = CacheEntryStatus.VALID
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.timestamp > self.ttl
    
    def is_valid(self) -> bool:
        """Check if the cache entry is valid (not expired or invalidated)."""
        return self.status == CacheEntryStatus.VALID and not self.is_expired()
    
    def touch(self) -> None:
        """Update last access time and increment access count."""
        self.last_access = time.time()
        self.access_count += 1
    
    def invalidate(self) -> None:
        """Mark the cache entry as invalidated."""
        self.status = CacheEntryStatus.INVALIDATED


@dataclass
class CacheStatistics:
    """Statistics for cache performance."""
    
    hits: int = 0
    misses: int = 0
    invalidations: int = 0
    refreshes: int = 0
    total_entries: int = 0
    expired_entries: int = 0
    memory_usage_bytes: int = 0
    
    @property
    def total_requests(self) -> int:
        """Total number of cache requests."""
        return self.hits + self.misses
    
    @property
    def hit_rate(self) -> float:
        """Cache hit rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100.0
    
    @property
    def miss_rate(self) -> float:
        """Cache miss rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.misses / self.total_requests) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'invalidations': self.invalidations,
            'refreshes': self.refreshes,
            'total_entries': self.total_entries,
            'expired_entries': self.expired_entries,
            'memory_usage_bytes': self.memory_usage_bytes,
            'total_requests': self.total_requests,
            'hit_rate': round(self.hit_rate, 2),
            'miss_rate': round(self.miss_rate, 2)
        }


class CacheCategory(Enum):
    """Categories of cached data."""
    
    GPIO = "gpio"
    SENSOR = "sensor"
    POSITION = "position"
    FAN = "fan"
    PWM = "pwm"
    PRINTER_STATE = "printer_state"
    ACTUATOR = "actuator"
    CUSTOM = "custom"


class StateCacheManager:
    """Manages hardware state caching with TTL support and automatic invalidation."""
    
    # Default TTL values for different categories (in seconds)
    DEFAULT_TTLS = {
        CacheCategory.GPIO: 1.0,
        CacheCategory.SENSOR: 0.5,
        CacheCategory.POSITION: 0.1,
        CacheCategory.FAN: 1.0,
        CacheCategory.PWM: 1.0,
        CacheCategory.PRINTER_STATE: 2.0,
        CacheCategory.ACTUATOR: 1.0,
        CacheCategory.CUSTOM: 5.0
    }
    
    def __init__(self,
                 moonraker_host: str = 'localhost',
                 moonraker_port: int = 7125,
                 moonraker_api_key: Optional[str] = None,
                 default_ttl: float = 1.0,
                 max_cache_size: int = 10000,
                 cleanup_interval: float = 10.0,
                 enable_auto_refresh: bool = True):
        """Initialize the state cache manager.
        
        Args:
            moonraker_host: Moonraker host address
            moonraker_port: Moonraker port
            moonraker_api_key: Optional Moonraker API key
            default_ttl: Default TTL for cache entries
            max_cache_size: Maximum number of cache entries
            cleanup_interval: Interval for expired entry cleanup (seconds)
            enable_auto_refresh: Enable automatic cache refresh
        """
        self.moonraker_host = moonraker_host
        self.moonraker_port = moonraker_port
        self.moonraker_api_key = moonraker_api_key
        self.base_url = f"http://{moonraker_host}:{moonraker_port}"
        
        # Cache configuration
        self.default_ttl = default_ttl
        self.max_cache_size = max_cache_size
        self.cleanup_interval = cleanup_interval
        self.enable_auto_refresh = enable_auto_refresh
        
        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._category_index: Dict[CacheCategory, Set[str]] = defaultdict(set)
        
        # Statistics
        self._stats = CacheStatistics()
        
        # Fetch functions for different categories
        self._fetch_functions: Dict[CacheCategory, Callable] = {}
        self._initialize_fetch_functions()
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # WebSocket integration
        self._websocket_client: Optional[aiohttp.ClientSession] = None
        self._websocket_connected = False
        
        logger.info(f"State cache manager initialized with default_ttl={default_ttl}s, "
                   f"max_size={max_cache_size}")
    
    def _initialize_fetch_functions(self) -> None:
        """Initialize fetch functions for different cache categories."""
        self._fetch_functions = {
            CacheCategory.GPIO: self._fetch_gpio_states,
            CacheCategory.SENSOR: self._fetch_sensor_data,
            CacheCategory.POSITION: self._fetch_position_data,
            CacheCategory.FAN: self._fetch_fan_states,
            CacheCategory.PWM: self._fetch_pwm_states,
            CacheCategory.PRINTER_STATE: self._fetch_printer_state,
            CacheCategory.ACTUATOR: self._fetch_actuator_states
        }
    
    async def start(self) -> None:
        """Start the cache manager and background tasks."""
        if self._running:
            logger.warning("Cache manager is already running")
            return
        
        self._running = True
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Connect to WebSocket for real-time updates
        await self._connect_websocket()
        
        logger.info("State cache manager started")
    
    async def stop(self) -> None:
        """Stop the cache manager and cleanup resources."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect WebSocket
        await self._disconnect_websocket()
        
        # Clear cache
        await self.clear()
        
        logger.info("State cache manager stopped")
    
    async def get(self, key: str, category: Optional[CacheCategory] = None,
                 force_refresh: bool = False) -> Optional[Any]:
        """Get a value from cache, fetching if expired or missing.
        
        Args:
            key: Cache key
            category: Cache category (for auto-fetch)
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            Cached value or None if not found
        """
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry and entry.is_valid() and not force_refresh:
                # Cache hit
                entry.touch()
                self._stats.hits += 1
                logger.debug(f"Cache hit: {key}")
                return entry.value
            
            # Cache miss or expired
            if entry:
                logger.debug(f"Cache expired: {key}")
            else:
                logger.debug(f"Cache miss: {key}")
            
            self._stats.misses += 1
            
            # Try to fetch fresh data if category is provided
            if category and category in self._fetch_functions:
                try:
                    fetch_func = self._fetch_functions[category]
                    fresh_data = await fetch_func(key)
                    
                    if fresh_data is not None:
                        await self.set(key, fresh_data, category=category)
                        self._stats.refreshes += 1
                        return fresh_data
                except Exception as e:
                    logger.error(f"Error fetching data for {key}: {e}")
            
            # Return cached value even if expired (as fallback)
            if entry:
                return entry.value
            
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None,
                  category: Optional[CacheCategory] = None) -> None:
        """Set a value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
            category: Cache category
        """
        async with self._lock:
            # Determine TTL
            if ttl is None and category:
                ttl = self.DEFAULT_TTLS.get(category, self.default_ttl)
            elif ttl is None:
                ttl = self.default_ttl
            
            # Create cache entry
            entry = CacheEntry(key=key, value=value, ttl=ttl)
            
            # Check cache size limit
            if len(self._cache) >= self.max_cache_size:
                await self._evict_oldest()
            
            # Store entry
            self._cache[key] = entry
            
            # Update category index
            if category:
                self._category_index[category].add(key)
            
            # Update statistics
            self._stats.total_entries = len(self._cache)
            self._stats.memory_usage_bytes = self._estimate_memory_usage()
            
            logger.debug(f"Cache set: {key} (ttl={ttl}s)")
    
    async def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if entry was invalidated, False if not found
        """
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry:
                entry.invalidate()
                self._stats.invalidations += 1
                logger.debug(f"Cache invalidated: {key}")
                return True
            
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache entries matching a pattern.
        
        Args:
            pattern: Regular expression pattern to match keys
            
        Returns:
            Number of entries invalidated
        """
        async with self._lock:
            count = 0
            regex = re.compile(pattern)
            
            for key in list(self._cache.keys()):
                if regex.match(key):
                    await self.invalidate(key)
                    count += 1
            
            logger.debug(f"Invalidated {count} entries matching pattern: {pattern}")
            return count
    
    async def invalidate_category(self, category: CacheCategory) -> int:
        """Invalidate all cache entries in a category.
        
        Args:
            category: Cache category to invalidate
            
        Returns:
            Number of entries invalidated
        """
        async with self._lock:
            count = 0
            keys = self._category_index.get(category, set()).copy()
            
            for key in keys:
                if await self.invalidate(key):
                    count += 1
            
            logger.debug(f"Invalidated {count} entries in category: {category.value}")
            return count
    
    async def refresh(self, key: str, category: Optional[CacheCategory] = None) -> bool:
        """Refresh a cache entry by fetching fresh data.
        
        Args:
            key: Cache key to refresh
            category: Cache category (for auto-fetch)
            
        Returns:
            True if refresh was successful, False otherwise
        """
        try:
            # Fetch fresh data
            if category and category in self._fetch_functions:
                fetch_func = self._fetch_functions[category]
                fresh_data = await fetch_func(key)
                
                if fresh_data is not None:
                    await self.set(key, fresh_data, category=category)
                    self._stats.refreshes += 1
                    logger.debug(f"Cache refreshed: {key}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error refreshing cache entry {key}: {e}")
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._category_index.clear()
            self._stats.total_entries = 0
            self._stats.memory_usage_bytes = 0
            logger.info("Cache cleared")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        async with self._lock:
            # Count expired entries
            expired = sum(1 for entry in self._cache.values() if entry.is_expired())
            self._stats.expired_entries = expired
            
            return self._stats.to_dict()
    
    async def warm_cache(self, keys: List[Tuple[str, CacheCategory]]) -> int:
        """Warm the cache by pre-fetching frequently accessed data.
        
        Args:
            keys: List of (key, category) tuples to warm
            
        Returns:
            Number of entries successfully warmed
        """
        count = 0
        
        for key, category in keys:
            try:
                if await self.refresh(key, category):
                    count += 1
            except Exception as e:
                logger.error(f"Error warming cache for {key}: {e}")
        
        logger.info(f"Cache warmed with {count}/{len(keys)} entries")
        return count
    
    async def get_category_keys(self, category: CacheCategory) -> List[str]:
        """Get all keys in a specific category.
        
        Args:
            category: Cache category
            
        Returns:
            List of keys in the category
        """
        async with self._lock:
            return list(self._category_index.get(category, set()))
    
    async def get_all_keys(self) -> List[str]:
        """Get all cache keys.
        
        Returns:
            List of all cache keys
        """
        async with self._lock:
            return list(self._cache.keys())
    
    # Fetch functions for different categories
    
    async def _fetch_gpio_states(self, key: str) -> Optional[Dict[str, Any]]:
        """Fetch GPIO states from Moonraker.
        
        Args:
            key: Cache key (pin name or 'all')
            
        Returns:
            GPIO state data
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.moonraker_api_key:
                    headers['X-Api-Key'] = self.moonraker_api_key
                
                if key == 'all' or key == 'gpio:all':
                    url = f"{self.base_url}/api/gpio_monitor/inputs"
                else:
                    pin_name = key.replace('gpio:', '')
                    url = f"{self.base_url}/api/gpio_monitor/input/{pin_name}"
                
                async with session.get(url, headers=headers) as response:
                    data = await response.json()
                    
                    if data.get('success'):
                        return data
                    
                    return None
        except Exception as e:
            logger.error(f"Error fetching GPIO states: {e}")
            return None
    
    async def _fetch_sensor_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Fetch sensor data from Moonraker.
        
        Args:
            key: Cache key (sensor name, type, or 'all')
            
        Returns:
            Sensor data
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.moonraker_api_key:
                    headers['X-Api-Key'] = self.moonraker_api_key
                
                if key == 'all' or key == 'sensor:all':
                    url = f"{self.base_url}/api/sensor_query/all"
                elif key.startswith('sensor:type:'):
                    sensor_type = key.replace('sensor:type:', '')
                    url = f"{self.base_url}/api/sensor_query/type/{sensor_type}"
                else:
                    sensor_name = key.replace('sensor:', '')
                    url = f"{self.base_url}/api/sensor_query/{sensor_name}"
                
                async with session.get(url, headers=headers) as response:
                    data = await response.json()
                    
                    if data.get('success'):
                        return data
                    
                    return None
        except Exception as e:
            logger.error(f"Error fetching sensor data: {e}")
            return None
    
    async def _fetch_position_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Fetch position data from Moonraker.
        
        Args:
            key: Cache key (ignored for position)
            
        Returns:
            Position data
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.moonraker_api_key:
                    headers['X-Api-Key'] = self.moonraker_api_key
                
                url = f"{self.base_url}/api/printer/query"
                payload = {'objects': {'toolhead': None}}
                
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()
                    
                    if data.get('result'):
                        return {
                            'success': True,
                            'position': data['result'].get('toolhead', {})
                        }
                    
                    return None
        except Exception as e:
            logger.error(f"Error fetching position data: {e}")
            return None
    
    async def _fetch_fan_states(self, key: str) -> Optional[Dict[str, Any]]:
        """Fetch fan states from Moonraker.
        
        Args:
            key: Cache key (fan name or 'all')
            
        Returns:
            Fan state data
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.moonraker_api_key:
                    headers['X-Api-Key'] = self.moonraker_api_key
                
                url = f"{self.base_url}/api/printer/query"
                payload = {'objects': {'fan': None}}
                
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()
                    
                    if data.get('result'):
                        return {
                            'success': True,
                            'fan': data['result'].get('fan', {})
                        }
                    
                    return None
        except Exception as e:
            logger.error(f"Error fetching fan states: {e}")
            return None
    
    async def _fetch_pwm_states(self, key: str) -> Optional[Dict[str, Any]]:
        """Fetch PWM states from Moonraker.
        
        Args:
            key: Cache key (pin name or 'all')
            
        Returns:
            PWM state data
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.moonraker_api_key:
                    headers['X-Api-Key'] = self.moonraker_api_key
                
                url = f"{self.base_url}/api/printer/query"
                payload = {'objects': {'output_pin': None}}
                
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()
                    
                    if data.get('result'):
                        return {
                            'success': True,
                            'output_pin': data['result'].get('output_pin', {})
                        }
                    
                    return None
        except Exception as e:
            logger.error(f"Error fetching PWM states: {e}")
            return None
    
    async def _fetch_printer_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Fetch printer state from Moonraker.
        
        Args:
            key: Cache key (ignored)
            
        Returns:
            Printer state data
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.moonraker_api_key:
                    headers['X-Api-Key'] = self.moonraker_api_key
                
                url = f"{self.base_url}/api/printer/query"
                payload = {'objects': {'print_stats': None, 'idle_timeout': None}}
                
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()
                    
                    if data.get('result'):
                        return {
                            'success': True,
                            'printer_state': data['result']
                        }
                    
                    return None
        except Exception as e:
            logger.error(f"Error fetching printer state: {e}")
            return None
    
    async def _fetch_actuator_states(self, key: str) -> Optional[Dict[str, Any]]:
        """Fetch actuator states from Moonraker.
        
        Args:
            key: Cache key (actuator name or 'all')
            
        Returns:
            Actuator state data
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.moonraker_api_key:
                    headers['X-Api-Key'] = self.moonraker_api_key
                
                url = f"{self.base_url}/api/printer/query"
                payload = {'objects': {'gcode_move': None}}
                
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()
                    
                    if data.get('result'):
                        return {
                            'success': True,
                            'gcode_move': data['result'].get('gcode_move', {})
                        }
                    
                    return None
        except Exception as e:
            logger.error(f"Error fetching actuator states: {e}")
            return None
    
    # Background tasks
    
    async def _cleanup_loop(self) -> None:
        """Background loop for cleaning up expired cache entries."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_expired(self) -> int:
        """Remove expired and invalidated entries from cache.
        
        Returns:
            Number of entries removed
        """
        async with self._lock:
            removed = 0
            keys_to_remove = []
            
            for key, entry in self._cache.items():
                if not entry.is_valid():
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                # Remove from cache
                del self._cache[key]
                
                # Remove from category index
                for category_keys in self._category_index.values():
                    category_keys.discard(key)
                
                removed += 1
            
            # Update statistics
            self._stats.total_entries = len(self._cache)
            self._stats.memory_usage_bytes = self._estimate_memory_usage()
            
            if removed > 0:
                logger.debug(f"Cleaned up {removed} expired cache entries")
            
            return removed
    
    async def _evict_oldest(self) -> None:
        """Evict the oldest cache entry when cache is full."""
        if not self._cache:
            return
        
        # Find entry with oldest last access time
        oldest_key = min(self._cache.keys(), 
                        key=lambda k: self._cache[k].last_access)
        
        # Remove entry
        del self._cache[oldest_key]
        
        # Remove from category index
        for category_keys in self._category_index.values():
            category_keys.discard(oldest_key)
        
        logger.debug(f"Evicted oldest cache entry: {oldest_key}")
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of cache in bytes.
        
        Returns:
            Estimated memory usage in bytes
        """
        import sys
        total = 0
        
        for entry in self._cache.values():
            total += sys.getsizeof(entry)
            total += sys.getsizeof(entry.key)
            total += sys.getsizeof(entry.value)
        
        return total
    
    # WebSocket integration
    
    async def _connect_websocket(self) -> None:
        """Connect to Moonraker WebSocket for real-time updates."""
        try:
            ws_url = f"ws://{self.moonraker_host}:{self.moonraker_port}/websocket"
            
            async with aiohttp.ClientSession() as session:
                self._websocket_client = session
                
                async with session.ws_connect(ws_url) as ws:
                    self._websocket_connected = True
                    logger.info("Connected to Moonraker WebSocket")
                    
                    # Subscribe to relevant events
                    await self._subscribe_to_events(ws)
                    
                    # Listen for updates
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_websocket_message(msg.json())
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket error: {ws.exception()}")
                            break
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            logger.info("WebSocket connection closed")
                            break
                    
                    self._websocket_connected = False
                    
        except Exception as e:
            logger.error(f"Error connecting to WebSocket: {e}")
            self._websocket_connected = False
    
    async def _subscribe_to_events(self, ws) -> None:
        """Subscribe to Moonraker WebSocket events for cache invalidation.
        
        Args:
            ws: WebSocket connection
        """
        # Subscribe to status updates
        subscribe_msg = {
            "jsonrpc": "2.0",
            "method": "printer.objects.subscribe",
            "params": {
                "objects": {
                    "output_pin": None,
                    "fan": None,
                    "toolhead": None,
                    "temperature_sensor": None,
                    "heaters": None,
                    "print_stats": None
                }
            },
            "id": 1
        }
        
        await ws.send_json(subscribe_msg)
        logger.info("Subscribed to Moonraker status updates")
    
    async def _handle_websocket_message(self, message: Dict[str, Any]) -> None:
        """Handle WebSocket message for cache invalidation.
        
        Args:
            message: WebSocket message
        """
        try:
            # Handle status updates
            if message.get('method') == 'notify_status_update':
                params = message.get('params', [])
                
                if params:
                    status_update = params[0]
                    await self._invalidate_on_status_update(status_update)
            
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def _invalidate_on_status_update(self, status_update: Dict[str, Any]) -> None:
        """Invalidate cache entries based on status update.
        
        Args:
            status_update: Status update from Moonraker
        """
        # Invalidate GPIO cache if output_pin changed
        if 'output_pin' in status_update:
            await self.invalidate_category(CacheCategory.GPIO)
            await self.invalidate_category(CacheCategory.PWM)
        
        # Invalidate fan cache if fan changed
        if 'fan' in status_update:
            await self.invalidate_category(CacheCategory.FAN)
        
        # Invalidate position cache if toolhead changed
        if 'toolhead' in status_update:
            await self.invalidate_category(CacheCategory.POSITION)
        
        # Invalidate sensor cache if temperature sensors changed
        if 'temperature_sensor' in status_update or 'heaters' in status_update:
            await self.invalidate_category(CacheCategory.SENSOR)
        
        # Invalidate printer state if print_stats changed
        if 'print_stats' in status_update:
            await self.invalidate_category(CacheCategory.PRINTER_STATE)
    
    async def _disconnect_websocket(self) -> None:
        """Disconnect from WebSocket."""
        if self._websocket_client:
            await self._websocket_client.close()
            self._websocket_client = None
            self._websocket_connected = False
            logger.info("Disconnected from WebSocket")


# Convenience functions

async def create_cache_manager(moonraker_host: str = 'localhost',
                              moonraker_port: int = 7125,
                              moonraker_api_key: Optional[str] = None,
                              default_ttl: float = 1.0,
                              max_cache_size: int = 10000,
                              cleanup_interval: float = 10.0,
                              enable_auto_refresh: bool = True,
                              auto_start: bool = True) -> StateCacheManager:
    """Create and optionally start a cache manager.
    
    Args:
        moonraker_host: Moonraker host address
        moonraker_port: Moonraker port
        moonraker_api_key: Optional Moonraker API key
        default_ttl: Default TTL for cache entries
        max_cache_size: Maximum number of cache entries
        cleanup_interval: Interval for expired entry cleanup (seconds)
        enable_auto_refresh: Enable automatic cache refresh
        auto_start: Automatically start the cache manager
        
    Returns:
        StateCacheManager instance
    """
    cache_manager = StateCacheManager(
        moonraker_host=moonraker_host,
        moonraker_port=moonraker_port,
        moonraker_api_key=moonraker_api_key,
        default_ttl=default_ttl,
        max_cache_size=max_cache_size,
        cleanup_interval=cleanup_interval,
        enable_auto_refresh=enable_auto_refresh
    )
    
    if auto_start:
        await cache_manager.start()
    
    return cache_manager
