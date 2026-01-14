#!/usr/bin/env python3
# Unit tests for State Cache Manager

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from dataclasses import dataclass


# Mock classes for testing
@dataclass
class CacheEntry:
    key: str
    value: any
    timestamp: float
    ttl: float
    access_count: int
    last_access: float
    status: str


class CacheStatistics:
    hits: int
    misses: int
    invalidations: int
    refreshes: int
    total_entries: int
    expired_entries: int
    memory_usage_bytes: int


class CacheCategory:
    GPIO = "gpio"
    SENSOR = "sensor"
    POSITION = "position"
    FAN = "fan"
    PWM = "pwm"
    PRINTER_STATE = "printer_state"
    ACTUATOR = "actuator"
    CUSTOM = "custom"


# Import cache module classes
from middleware.cache import (
    StateCacheManager,
    CacheEntryStatus,
    CacheStatistics,
    CacheCategory,
    CacheEntry
)


@pytest.fixture
def mock_aiohttp_session():
    """Create a mock aiohttp session."""
    session = Mock()
    session.get = AsyncMock()
    session.post = AsyncMock()
    session.ws_connect = MagicMock()
    return session


@pytest.fixture
def state_cache_manager():
    """Create a StateCacheManager instance for testing."""
    with patch('middleware.cache.aiohttp.ClientSession'):
        manager = StateCacheManager(
            moonraker_host='localhost',
            moonraker_port=7125,
            moonraker_api_key='test_key',
            default_ttl=1.0,
            max_cache_size=100,
            cleanup_interval=10.0,
            enable_auto_refresh=False  # Disable auto-start for testing
        )
        return manager


class TestCacheEntry:
    """Test CacheEntry dataclass."""
    
    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(
            key='test_key',
            value='test_value',
            ttl=5.0
        )
        
        assert entry.key == 'test_key'
        assert entry.value == 'test_value'
        assert entry.ttl == 5.0
        assert entry.access_count == 0
        assert entry.status == CacheEntryStatus.VALID
    
    def test_is_expired(self):
        """Test cache entry expiration check."""
        entry = CacheEntry(
            key='test_key',
            value='test_value',
            timestamp=time.time() - 10.0,
            ttl=5.0
        )
        
        assert entry.is_expired() == True
    
    def test_is_not_expired(self):
        """Test cache entry not expired."""
        entry = CacheEntry(
            key='test_key',
            value='test_value',
            timestamp=time.time(),
            ttl=5.0
        )
        
        assert entry.is_expired() == False
    
    def test_is_valid(self):
        """Test cache entry validity."""
        entry = CacheEntry(
            key='test_key',
            value='test_value',
            timestamp=time.time(),
            ttl=5.0
        )
        
        assert entry.is_valid() == True
    
    def test_is_invalid_expired(self):
        """Test cache entry invalid when expired."""
        entry = CacheEntry(
            key='test_key',
            value='test_value',
            timestamp=time.time() - 10.0,
            ttl=5.0
        )
        
        assert entry.is_valid() == False
    
    def test_is_invalid_status(self):
        """Test cache entry invalid when status is INVALIDATED."""
        entry = CacheEntry(
            key='test_key',
            value='test_value',
            timestamp=time.time(),
            ttl=5.0,
            status=CacheEntryStatus.INVALIDATED
        )
        
        assert entry.is_valid() == False
    
    def test_touch(self):
        """Test cache entry touch method."""
        entry = CacheEntry(
            key='test_key',
            value='test_value',
            timestamp=time.time(),
            ttl=5.0
        )
        
        original_count = entry.access_count
        original_last_access = entry.last_access
        
        time.sleep(0.1)  # Small delay
        entry.touch()
        
        assert entry.access_count == original_count + 1
        assert entry.last_access > original_last_access
    
    def test_invalidate(self):
        """Test cache entry invalidate method."""
        entry = CacheEntry(
            key='test_key',
            value='test_value',
            timestamp=time.time(),
            ttl=5.0
        )
        
        entry.invalidate()
        
        assert entry.status == CacheEntryStatus.INVALIDATED


class TestCacheStatistics:
    """Test CacheStatistics dataclass."""
    
    def test_statistics_creation(self):
        """Test creating cache statistics."""
        stats = CacheStatistics(
            hits=100,
            misses=20,
            invalidations=5,
            refreshes=10,
            total_entries=50,
            expired_entries=2,
            memory_usage_bytes=1024
        )
        
        assert stats.hits == 100
        assert stats.misses == 20
        assert stats.invalidations == 5
        assert stats.refreshes == 10
        assert stats.total_entries == 50
        assert stats.expired_entries == 2
        assert stats.memory_usage_bytes == 1024
    
    def test_total_requests(self):
        """Test total requests calculation."""
        stats = CacheStatistics(hits=100, misses=20)
        
        assert stats.total_requests == 120
    
    def test_hit_rate(self):
        """Test hit rate calculation."""
        stats = CacheStatistics(hits=80, misses=20)
        
        assert stats.hit_rate == 80.0
    
    def test_hit_rate_zero_requests(self):
        """Test hit rate with zero requests."""
        stats = CacheStatistics(hits=0, misses=0)
        
        assert stats.hit_rate == 0.0
    
    def test_miss_rate(self):
        """Test miss rate calculation."""
        stats = CacheStatistics(hits=80, misses=20)
        
        assert stats.miss_rate == 20.0
    
    def test_to_dict(self):
        """Test statistics to dictionary conversion."""
        stats = CacheStatistics(hits=100, misses=20)
        
        result = stats.to_dict()
        
        assert result['hits'] == 100
        assert result['misses'] == 20
        assert result['total_requests'] == 120
        assert result['hit_rate'] == 83.33  # Rounded
        assert result['miss_rate'] == 16.67  # Rounded


class TestStateCacheManagerInitialization:
    """Test StateCacheManager initialization."""
    
    def test_initialization_with_defaults(self):
        """Test initialization with default values."""
        with patch('middleware.cache.aiohttp.ClientSession'):
            manager = StateCacheManager(
                moonraker_host='localhost',
                moonraker_port=7125,
                enable_auto_refresh=False
            )
            
            assert manager.moonraker_host == 'localhost'
            assert manager.moonraker_port == 7125
            assert manager.default_ttl == 1.0
            assert manager.max_cache_size == 10000
            assert manager.cleanup_interval == 10.0
            assert manager.enable_auto_refresh == True
    
    def test_initialization_with_custom_values(self):
        """Test initialization with custom values."""
        with patch('middleware.cache.aiohttp.ClientSession'):
            manager = StateCacheManager(
                moonraker_host='192.168.1.100',
                moonraker_port=8080,
                moonraker_api_key='custom_key',
                default_ttl=2.0,
                max_cache_size=500,
                cleanup_interval=5.0,
                enable_auto_refresh=False
            )
            
            assert manager.moonraker_host == '192.168.1.100'
            assert manager.moonraker_port == 8080
            assert manager.moonraker_api_key == 'custom_key'
            assert manager.default_ttl == 2.0
            assert manager.max_cache_size == 500
            assert manager.cleanup_interval == 5.0
    
    def test_initialization_empty_cache(self):
        """Test that cache starts empty."""
        with patch('middleware.cache.aiohttp.ClientSession'):
            manager = StateCacheManager(
                enable_auto_refresh=False
            )
            
            assert len(manager._cache) == 0
            assert len(manager._category_index) == 0


class TestCacheGet:
    """Test cache get operations."""
    
    @pytest.mark.asyncio
    async def test_get_cache_hit(self, state_cache_manager):
        """Test cache hit."""
        # Set a value
        await state_cache_manager.set('test_key', 'test_value', ttl=5.0)
        
        # Get the value
        value = await state_cache_manager.get('test_key')
        
        assert value == 'test_value'
        
        # Check statistics
        stats = await state_cache_manager.get_statistics()
        assert stats['hits'] == 1
        assert stats['misses'] == 0
    
    @pytest.mark.asyncio
    async def test_get_cache_miss(self, state_cache_manager):
        """Test cache miss."""
        # Get non-existent value
        value = await state_cache_manager.get('nonexistent_key')
        
        assert value is None
        
        # Check statistics
        stats = await state_cache_manager.get_statistics()
        assert stats['hits'] == 0
        assert stats['misses'] == 1
    
    @pytest.mark.asyncio
    async def test_get_expired_entry(self, state_cache_manager):
        """Test getting expired entry."""
        # Set a value with short TTL
        await state_cache_manager.set('test_key', 'test_value', ttl=0.1)
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Get the value (should return None or old value)
        value = await state_cache_manager.get('test_key')
        
        # Value should be None since no fetch function is provided
        assert value is None
    
    @pytest.mark.asyncio
    async def test_get_force_refresh(self, state_cache_manager):
        """Test force refresh."""
        # Set a value
        await state_cache_manager.set('test_key', 'old_value', ttl=5.0)
        
        # Force refresh (should return None since no fetch function)
        value = await state_cache_manager.get('test_key', force_refresh=True)
        
        # Value should be None since no fetch function is provided
        assert value is None
    
    @pytest.mark.asyncio
    async def test_get_with_category(self, state_cache_manager):
        """Test getting with category."""
        # Set a value with category
        await state_cache_manager.set(
            'test_key',
            'test_value',
            category=CacheCategory.GPIO
        )
        
        # Get the value
        value = await state_cache_manager.get(
            'test_key',
            category=CacheCategory.GPIO
        )
        
        assert value == 'test_value'


class TestCacheSet:
    """Test cache set operations."""
    
    @pytest.mark.asyncio
    async def test_set_value(self, state_cache_manager):
        """Test setting a value."""
        await state_cache_manager.set('test_key', 'test_value')
        
        # Get the value
        value = await state_cache_manager.get('test_key')
        
        assert value == 'test_value'
    
    @pytest.mark.asyncio
    async def test_set_with_ttl(self, state_cache_manager):
        """Test setting a value with TTL."""
        await state_cache_manager.set('test_key', 'test_value', ttl=10.0)
        
        # Get the entry
        entry = state_cache_manager._cache.get('test_key')
        
        assert entry is not None
        assert entry.ttl == 10.0
    
    @pytest.mark.asyncio
    async def test_set_with_category(self, state_cache_manager):
        """Test setting a value with category."""
        await state_cache_manager.set(
            'test_key',
            'test_value',
            category=CacheCategory.GPIO
        )
        
        # Verify category index
        keys = await state_cache_manager.get_category_keys(CacheCategory.GPIO)
        
        assert 'test_key' in keys
    
    @pytest.mark.asyncio
    async def test_set_with_default_ttl(self, state_cache_manager):
        """Test setting a value with default TTL."""
        await state_cache_manager.set('test_key', 'test_value')
        
        # Get the entry
        entry = state_cache_manager._cache.get('test_key')
        
        assert entry is not None
        assert entry.ttl == state_cache_manager.default_ttl
    
    @pytest.mark.asyncio
    async def test_set_overwrite(self, state_cache_manager):
        """Test overwriting existing value."""
        # Set initial value
        await state_cache_manager.set('test_key', 'old_value')
        
        # Overwrite
        await state_cache_manager.set('test_key', 'new_value')
        
        # Get the value
        value = await state_cache_manager.get('test_key')
        
        assert value == 'new_value'


class TestCacheInvalidate:
    """Test cache invalidation operations."""
    
    @pytest.mark.asyncio
    async def test_invalidate_key(self, state_cache_manager):
        """Test invalidating a specific key."""
        # Set a value
        await state_cache_manager.set('test_key', 'test_value')
        
        # Invalidate
        result = await state_cache_manager.invalidate('test_key')
        
        assert result == True
        
        # Verify entry is invalidated
        entry = state_cache_manager._cache.get('test_key')
        assert entry is not None
        assert entry.status == CacheEntryStatus.INVALIDATED
    
    @pytest.mark.asyncio
    async def test_invalidate_nonexistent_key(self, state_cache_manager):
        """Test invalidating non-existent key."""
        result = await state_cache_manager.invalidate('nonexistent_key')
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, state_cache_manager):
        """Test invalidating by pattern."""
        # Set multiple values
        await state_cache_manager.set('gpio:pin1', 'value1')
        await state_cache_manager.set('gpio:pin2', 'value2')
        await state_cache_manager.set('sensor:temp1', 'value3')
        
        # Invalidate pattern
        count = await state_cache_manager.invalidate_pattern('gpio:.*')
        
        assert count == 2
        
        # Verify only sensor key remains
        assert 'gpio:pin1' not in state_cache_manager._cache
        assert 'gpio:pin2' not in state_cache_manager._cache
        assert 'sensor:temp1' in state_cache_manager._cache
    
    @pytest.mark.asyncio
    async def test_invalidate_category(self, state_cache_manager):
        """Test invalidating by category."""
        # Set values in different categories
        await state_cache_manager.set('gpio:pin1', 'value1', category=CacheCategory.GPIO)
        await state_cache_manager.set('sensor:temp1', 'value2', category=CacheCategory.SENSOR)
        await state_cache_manager.set('gpio:pin2', 'value3', category=CacheCategory.GPIO)
        
        # Invalidate GPIO category
        count = await state_cache_manager.invalidate_category(CacheCategory.GPIO)
        
        assert count == 2
        
        # Verify only sensor key remains
        assert 'gpio:pin1' not in state_cache_manager._cache
        assert 'gpio:pin2' not in state_cache_manager._cache
        assert 'sensor:temp1' in state_cache_manager._cache


class TestCacheRefresh:
    """Test cache refresh operations."""
    
    @pytest.mark.asyncio
    async def test_refresh_key(self, state_cache_manager):
        """Test refreshing a specific key."""
        # Set a value
        await state_cache_manager.set('test_key', 'old_value')
        
        # Refresh (should return False since no fetch function)
        result = await state_cache_manager.refresh('test_key')
        
        assert result == False


class TestCacheClear:
    """Test cache clear operations."""
    
    @pytest.mark.asyncio
    async def test_clear_all(self, state_cache_manager):
        """Test clearing all cache entries."""
        # Set some values
        await state_cache_manager.set('key1', 'value1')
        await state_cache_manager.set('key2', 'value2')
        await state_cache_manager.set('key3', 'value3')
        
        # Clear
        await state_cache_manager.clear()
        
        # Verify empty
        assert len(state_cache_manager._cache) == 0
        assert len(state_cache_manager._category_index) == 0
        
        # Verify statistics
        stats = await state_cache_manager.get_statistics()
        assert stats['total_entries'] == 0


class TestCacheStatistics:
    """Test cache statistics operations."""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, state_cache_manager):
        """Test getting cache statistics."""
        # Set some values
        await state_cache_manager.set('key1', 'value1')
        await state_cache_manager.set('key2', 'value2')
        
        # Get and get (cache miss)
        await state_cache_manager.get('key1')
        await state_cache_manager.get('nonexistent')
        
        # Get statistics
        stats = await state_cache_manager.get_statistics()
        
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['total_requests'] == 2
        assert stats['hit_rate'] == 50.0
        assert stats['miss_rate'] == 50.0


class TestCacheCategoryOperations:
    """Test cache category operations."""
    
    @pytest.mark.asyncio
    async def test_get_category_keys(self, state_cache_manager):
        """Test getting keys in a category."""
        # Set values in different categories
        await state_cache_manager.set('gpio:pin1', 'value1', category=CacheCategory.GPIO)
        await state_cache_manager.set('gpio:pin2', 'value2', category=CacheCategory.GPIO)
        await state_cache_manager.set('sensor:temp1', 'value3', category=CacheCategory.SENSOR)
        
        # Get GPIO keys
        keys = await state_cache_manager.get_category_keys(CacheCategory.GPIO)
        
        assert len(keys) == 2
        assert 'gpio:pin1' in keys
        assert 'gpio:pin2' in keys
        assert 'sensor:temp1' not in keys
    
    @pytest.mark.asyncio
    async def test_get_all_keys(self, state_cache_manager):
        """Test getting all cache keys."""
        # Set some values
        await state_cache_manager.set('key1', 'value1')
        await state_cache_manager.set('key2', 'value2')
        await state_cache_manager.set('key3', 'value3')
        
        # Get all keys
        keys = await state_cache_manager.get_all_keys()
        
        assert len(keys) == 3
        assert 'key1' in keys
        assert 'key2' in keys
        assert 'key3' in keys


class TestCacheWarmCache:
    """Test cache warming operations."""
    
    @pytest.mark.asyncio
    async def test_warm_cache(self, state_cache_manager):
        """Test warming cache with multiple keys."""
        keys_to_warm = [
            ('gpio:pin1', CacheCategory.GPIO),
            ('sensor:temp1', CacheCategory.SENSOR)
        ]
        
        # Warm cache (should return 0 since no fetch functions)
        count = await state_cache_manager.warm_cache(keys_to_warm)
        
        assert count == 0


class TestCacheEviction:
    """Test cache eviction when full."""
    
    @pytest.mark.asyncio
    async def test_evict_oldest(self, state_cache_manager):
        """Test evicting oldest entry when cache is full."""
        # Create a cache with small max size
        with patch('middleware.cache.aiohttp.ClientSession'):
            small_cache = StateCacheManager(
                max_cache_size=2,
                enable_auto_refresh=False
            )
            
            # Fill cache
            await small_cache.set('key1', 'value1')
            await small_cache.set('key2', 'value2')
            
            # Access key1 to make it most recent
            await small_cache.get('key1')
            
            # Add third entry (should evict key2)
            await small_cache.set('key3', 'value3')
            
            # Verify key2 was evicted
            assert 'key1' in small_cache._cache
            assert 'key3' in small_cache._cache
            assert 'key2' not in small_cache._cache


class TestCacheLifecycle:
    """Test cache lifecycle operations."""
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self, state_cache_manager):
        """Test starting and stopping cache manager."""
        # Start
        await state_cache_manager.start()
        
        assert state_cache_manager._running == True
        
        # Stop
        await state_cache_manager.stop()
        
        assert state_cache_manager._running == False
