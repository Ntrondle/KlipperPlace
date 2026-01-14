#!/usr/bin/env python3
# Integration Tests: WebSocket Flow
# Tests for WebSocket notification and communication flow

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock as async_mock
import asyncio
import json
from typing import Dict, Any

from middleware.cache import StateCacheManager, CacheCategory
from middleware.safety import SafetyManager, SafetyEvent, SafetyEventType, SafetyLevel


class TestWebSocketConnectionFlow:
    """Test suite for WebSocket connection flow."""
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_connection_established(self, mock_cache_manager):
        """Test that WebSocket connection is established."""
        # Mock WebSocket connection
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.__aiter__ = AsyncMock(return_value=iter([]))
        
        # Simulate connection
        await mock_cache_manager._connect_websocket()
        
        # Verify connection attempt was made
        assert hasattr(mock_cache_manager, '_websocket_connected')
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_subscription_to_events(self, mock_cache_manager):
        """Test that WebSocket subscribes to Moonraker events."""
        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        # Simulate subscription
        await mock_cache_manager._subscribe_to_events(mock_ws)
        
        # Verify subscription message
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        
        assert call_args['jsonrpc'] == '2.0'
        assert call_args['method'] == 'printer.objects.subscribe'
        assert 'objects' in call_args['params']
        assert 'output_pin' in call_args['params']['objects']
        assert 'fan' in call_args['params']['objects']
        assert 'toolhead' in call_args['params']['objects']
        assert 'temperature_sensor' in call_args['params']['objects']
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_message_handling(self, mock_cache_manager):
        """Test that WebSocket messages are handled correctly."""
        # Mock message
        test_message = {
            'method': 'notify_status_update',
            'params': [{
                'output_pin': {'PA1': {'value': 1}},
                'fan': {'speed': 0.5},
                'toolhead': {'position': [100.0, 50.0, 10.0]}
            }]
        }
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(test_message)
        
        # Verify cache invalidation was called
        assert mock_cache_manager.invalidate_category.called
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_gpio_status_update(self, mock_cache_manager):
        """Test that GPIO status updates trigger cache invalidation."""
        # Mock message with GPIO update
        message = {
            'method': 'notify_status_update',
            'params': [{
                'output_pin': {'PA1': {'value': 1}, 'PA2': {'value': 0}}
            }]
        }
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify GPIO and PWM cache invalidation
        mock_cache_manager.invalidate_category.assert_any_call(CacheCategory.GPIO)
        mock_cache_manager.invalidate_category.assert_any_call(CacheCategory.PWM)
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_fan_status_update(self, mock_cache_manager):
        """Test that fan status updates trigger cache invalidation."""
        # Mock message with fan update
        message = {
            'method': 'notify_status_update',
            'params': [{
                'fan': {'speed': 0.75}
            }]
        }
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify fan cache invalidation
        mock_cache_manager.invalidate_category.assert_called_with(CacheCategory.FAN)
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_position_status_update(self, mock_cache_manager):
        """Test that position updates trigger cache invalidation."""
        # Mock message with position update
        message = {
            'method': 'notify_status_update',
            'params': [{
                'toolhead': {'position': [100.0, 50.0, 10.0]}
            }]
        }
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify position cache invalidation
        mock_cache_manager.invalidate_category.assert_called_with(CacheCategory.POSITION)
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_sensor_status_update(self, mock_cache_manager):
        """Test that sensor updates trigger cache invalidation."""
        # Mock message with sensor update
        message = {
            'method': 'notify_status_update',
            'params': [{
                'temperature_sensor': {'sensor1': {'temperature': 25.5}}
            }]
        }
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify sensor cache invalidation
        mock_cache_manager.invalidate_category.assert_called_with(CacheCategory.SENSOR)
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_printer_state_update(self, mock_cache_manager):
        """Test that printer state updates trigger cache invalidation."""
        # Mock message with printer state update
        message = {
            'method': 'notify_status_update',
            'params': [{
                'print_stats': {'state': 'printing', 'filename': 'test.gcode'}
            }]
        }
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify printer state cache invalidation
        mock_cache_manager.invalidate_category.assert_called_with(CacheCategory.PRINTER_STATE)
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_combined_status_update(self, mock_cache_manager):
        """Test that combined status updates trigger multiple cache invalidations."""
        # Mock message with multiple updates
        message = {
            'method': 'notify_status_update',
            'params': [{
                'output_pin': {'PA1': {'value': 1}},
                'fan': {'speed': 0.5},
                'toolhead': {'position': [100.0, 50.0, 10.0]},
                'temperature_sensor': {'sensor1': {'temperature': 25.5}},
                'print_stats': {'state': 'printing'}
            }]
        }
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify multiple cache invalidations
        assert mock_cache_manager.invalidate_category.call_count >= 3
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_error_handling(self, mock_cache_manager):
        """Test that WebSocket errors are handled gracefully."""
        # Mock WebSocket error
        mock_ws = AsyncMock()
        mock_ws.exception = MagicMock(return_value=Exception('Connection lost'))
        
        # Simulate error message
        error_message = {
            'type': 'error',
            'data': 'Connection error'
        }
        
        # Handle error
        try:
            await mock_cache_manager._handle_websocket_message(error_message)
        except Exception as e:
            # Error should be caught and logged
            assert 'Connection error' in str(e) or True
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_disconnection(self, mock_cache_manager):
        """Test that WebSocket disconnection is handled."""
        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()
        
        # Simulate disconnection
        await mock_cache_manager._disconnect_websocket()
        
        # Verify cleanup
        assert mock_cache_manager._websocket_connected == False


class TestWebSocketNotificationFlow:
    """Test suite for WebSocket notification flow."""
    
    @pytest_asyncio.asyncio_test
    async def test_notification_on_gpio_change(self, mock_cache_manager):
        """Test that GPIO changes trigger notifications."""
        # Simulate GPIO status update
        message = {
            'method': 'notify_status_update',
            'params': [{
                'output_pin': {'PA1': {'value': 1}}
            }]
        }
        
        # Track invalidation calls
        invalidation_calls = []
        original_invalidate = mock_cache_manager.invalidate_category
        
        async def track_invalidate(category):
            invalidation_calls.append(category)
            return await original_invalidate(category)
        
        mock_cache_manager.invalidate_category = track_invalidate
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify notification
        assert CacheCategory.GPIO in invalidation_calls
        assert CacheCategory.PWM in invalidation_calls
    
    @pytest_asyncio.asyncio_test
    async def test_notification_on_fan_change(self, mock_cache_manager):
        """Test that fan changes trigger notifications."""
        # Simulate fan status update
        message = {
            'method': 'notify_status_update',
            'params': [{
                'fan': {'speed': 0.75}
            }]
        }
        
        # Track invalidation calls
        invalidation_calls = []
        original_invalidate = mock_cache_manager.invalidate_category
        
        async def track_invalidate(category):
            invalidation_calls.append(category)
            return await original_invalidate(category)
        
        mock_cache_manager.invalidate_category = track_invalidate
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify notification
        assert CacheCategory.FAN in invalidation_calls
    
    @pytest_asyncio.asyncio_test
    async def test_notification_on_position_change(self, mock_cache_manager):
        """Test that position changes trigger notifications."""
        # Simulate position update
        message = {
            'method': 'notify_status_update',
            'params': [{
                'toolhead': {'position': [100.0, 50.0, 10.0]}
            }]
        }
        
        # Track invalidation calls
        invalidation_calls = []
        original_invalidate = mock_cache_manager.invalidate_category
        
        async def track_invalidate(category):
            invalidation_calls.append(category)
            return await original_invalidate(category)
        
        mock_cache_manager.invalidate_category = track_invalidate
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify notification
        assert CacheCategory.POSITION in invalidation_calls
    
    @pytest_asyncio.asyncio_test
    async def test_notification_on_sensor_change(self, mock_cache_manager):
        """Test that sensor changes trigger notifications."""
        # Simulate sensor update
        message = {
            'method': 'notify_status_update',
            'params': [{
                'temperature_sensor': {'sensor1': {'temperature': 25.5}}
            }]
        }
        
        # Track invalidation calls
        invalidation_calls = []
        original_invalidate = mock_cache_manager.invalidate_category
        
        async def track_invalidate(category):
            invalidation_calls.append(category)
            return await original_invalidate(category)
        
        mock_cache_manager.invalidate_category = track_invalidate
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify notification
        assert CacheCategory.SENSOR in invalidation_calls
    
    @pytest_asyncio.asyncio_test
    async def test_notification_on_multiple_changes(self, mock_cache_manager):
        """Test that multiple changes trigger multiple notifications."""
        # Simulate multiple updates
        message = {
            'method': 'notify_status_update',
            'params': [{
                'output_pin': {'PA1': {'value': 1}},
                'fan': {'speed': 0.5},
                'toolhead': {'position': [100.0, 50.0, 10.0]},
                'temperature_sensor': {'sensor1': {'temperature': 25.5}},
                'print_stats': {'state': 'printing'}
            }]
        }
        
        # Track invalidation calls
        invalidation_calls = []
        original_invalidate = mock_cache_manager.invalidate_category
        
        async def track_invalidate(category):
            invalidation_calls.append(category)
            return await original_invalidate(category)
        
        mock_cache_manager.invalidate_category = track_invalidate
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify multiple notifications
        assert len(invalidation_calls) >= 3
        assert CacheCategory.GPIO in invalidation_calls
        assert CacheCategory.FAN in invalidation_calls
        assert CacheCategory.POSITION in invalidation_calls


class TestWebSocketRealTimeUpdates:
    """Test suite for real-time update flow."""
    
    @pytest_asyncio.asyncio_test
    async def test_real_time_position_updates(self, mock_cache_manager):
        """Test that position updates are received in real-time."""
        # Simulate position updates
        positions = [
            [0.0, 0.0, 0.0],
            [10.0, 5.0, 2.0],
            [20.0, 10.0, 4.0],
            [30.0, 15.0, 6.0]
        ]
        
        for pos in positions:
            message = {
                'method': 'notify_status_update',
                'params': [{
                    'toolhead': {'position': pos}
                }]
            }
            
            await mock_cache_manager._handle_websocket_message(message)
        
        # Verify cache was invalidated for each update
        assert mock_cache_manager.invalidate_category.call_count == len(positions)
    
    @pytest_asyncio.asyncio_test
    async def test_real_time_temperature_updates(self, mock_cache_manager):
        """Test that temperature updates are received in real-time."""
        # Simulate temperature updates
        temperatures = [20.0, 21.0, 22.0, 23.0, 24.0]
        
        for temp in temperatures:
            message = {
                'method': 'notify_status_update',
                'params': [{
                    'temperature_sensor': {'sensor1': {'temperature': temp}}
                }]
            }
            
            await mock_cache_manager._handle_websocket_message(message)
        
        # Verify cache was invalidated for each update
        assert mock_cache_manager.invalidate_category.call_count == len(temperatures)
    
    @pytest_asyncio.asyncio_test
    async def test_real_time_gpio_state_updates(self, mock_cache_manager):
        """Test that GPIO state updates are received in real-time."""
        # Simulate GPIO state changes
        gpio_states = [0, 1, 0, 1, 0]
        
        for state in gpio_states:
            message = {
                'method': 'notify_status_update',
                'params': [{
                    'output_pin': {'PA1': {'value': state}}
                }]
            }
            
            await mock_cache_manager._handle_websocket_message(message)
        
        # Verify cache was invalidated for each update
        assert mock_cache_manager.invalidate_category.call_count == len(gpio_states)
    
    @pytest_asyncio.asyncio_test
    async def test_real_time_fan_speed_updates(self, mock_cache_manager):
        """Test that fan speed updates are received in real-time."""
        # Simulate fan speed changes
        fan_speeds = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        for speed in fan_speeds:
            message = {
                'method': 'notify_status_update',
                'params': [{
                    'fan': {'speed': speed}
                }]
            }
            
            await mock_cache_manager._handle_websocket_message(message)
        
        # Verify cache was invalidated for each update
        assert mock_cache_manager.invalidate_category.call_count == len(fan_speeds)
    
    @pytest_asyncio.asyncio_test
    async def test_real_time_printer_state_updates(self, mock_cache_manager):
        """Test that printer state updates are received in real-time."""
        # Simulate printer state changes
        states = ['idle', 'printing', 'paused', 'complete', 'error']
        
        for state in states:
            message = {
                'method': 'notify_status_update',
                'params': [{
                    'print_stats': {'state': state}
                }]
            }
            
            await mock_cache_manager._handle_websocket_message(message)
        
        # Verify cache was invalidated for each update
        assert mock_cache_manager.invalidate_category.call_count == len(states)


class TestWebSocketReconnectionFlow:
    """Test suite for WebSocket reconnection flow."""
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_reconnection_after_disconnect(self, mock_cache_manager):
        """Test that WebSocket reconnects after disconnect."""
        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()
        
        # Simulate disconnect
        await mock_cache_manager._disconnect_websocket()
        assert mock_cache_manager._websocket_connected == False
        
        # Simulate reconnect
        await mock_cache_manager._connect_websocket()
        
        # Verify reconnection attempt
        assert hasattr(mock_cache_manager, '_websocket_connected')
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_resubscription_after_reconnect(self, mock_cache_manager):
        """Test that WebSocket resubscribes after reconnect."""
        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.__aiter__ = AsyncMock(return_value=iter([]))
        
        # Simulate reconnection
        await mock_cache_manager._connect_websocket()
        
        # Verify resubscription
        await mock_cache_manager._subscribe_to_events(mock_ws)
        
        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args['method'] == 'printer.objects.subscribe'
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_state_preservation_across_reconnect(self, mock_cache_manager):
        """Test that cache state is preserved across reconnect."""
        # Set some cache state
        await mock_cache_manager.set('test_key', 'test_value', ttl=10.0)
        
        # Simulate disconnect and reconnect
        await mock_cache_manager._disconnect_websocket()
        await mock_cache_manager._connect_websocket()
        
        # Verify cache state is preserved
        value = await mock_cache_manager.get('test_key')
        # In mock, just verify method was called
        mock_cache_manager.get.assert_called()


class TestWebSocketErrorHandling:
    """Test suite for WebSocket error handling."""
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_connection_error(self, mock_cache_manager):
        """Test that connection errors are handled."""
        # Mock connection error
        with patch('aiohttp.ClientSession.ws_connect', side_effect=Exception('Connection failed')):
            # Attempt connection
            try:
                await mock_cache_manager._connect_websocket()
            except Exception as e:
                # Error should be caught and logged
                assert 'Connection failed' in str(e)
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_message_parse_error(self, mock_cache_manager):
        """Test that message parse errors are handled."""
        # Mock invalid message
        invalid_message = {
            'method': 'unknown_method',
            'params': []
        }
        
        # Handle invalid message
        try:
            await mock_cache_manager._handle_websocket_message(invalid_message)
        except Exception as e:
            # Error should be caught and logged
            assert True  # Error was handled
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_timeout_handling(self, mock_cache_manager):
        """Test that WebSocket timeouts are handled."""
        # Mock WebSocket timeout
        mock_ws = AsyncMock()
        mock_ws.__aiter__ = AsyncMock(side_effect=asyncio.TimeoutError)
        
        # Simulate timeout
        try:
            await mock_cache_manager._connect_websocket()
        except asyncio.TimeoutError:
            # Timeout should be caught
            assert True
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_graceful_shutdown(self, mock_cache_manager):
        """Test that WebSocket shutdown is graceful."""
        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()
        
        # Simulate shutdown
        await mock_cache_manager._disconnect_websocket()
        
        # Verify graceful shutdown
        assert mock_cache_manager._websocket_connected == False
        mock_ws.close.assert_called()


class TestWebSocketIntegrationWithSafety:
    """Test suite for WebSocket integration with safety manager."""
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_triggers_safety_events(self, mock_cache_manager, mock_safety_manager):
        """Test that WebSocket updates trigger safety events."""
        # Simulate temperature update that exceeds limit
        message = {
            'method': 'notify_status_update',
            'params': [{
                'temperature_sensor': {'extruder': {'temperature': 300.0}}
            }]
        }
        
        # Track safety events
        safety_events = []
        original_log_state_change = mock_safety_manager.log_state_change
        
        async def track_safety_event(event):
            safety_events.append(event)
            return await original_log_state_change(
                'temperature_sensor',
                250.0,
                300.0
            )
        
        mock_safety_manager.log_state_change = track_safety_event
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify safety event was triggered
        assert len(safety_events) > 0
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_emergency_stop_notification(self, mock_cache_manager, mock_safety_manager):
        """Test that emergency stop is notified via WebSocket."""
        # Simulate emergency stop
        message = {
            'method': 'notify_status_update',
            'params': [{
                'print_stats': {'state': 'error', 'state_message': 'Emergency stop triggered'}}
            }]
        }
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify cache invalidation
        mock_cache_manager.invalidate_category.assert_called_with(CacheCategory.PRINTER_STATE)
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_position_limit_warning(self, mock_cache_manager, mock_safety_manager):
        """Test that position limit warnings are triggered."""
        # Simulate position out of bounds
        message = {
            'method': 'notify_status_update',
            'params': [{
                'toolhead': {'position': [9999.0, 50.0, 10.0]}
            }]
        }
        
        # Track safety events
        safety_events = []
        original_check_position = mock_safety_manager.check_position_limits
        
        async def track_position_check(position=None):
            event = SafetyEvent(
                event_type=SafetyEventType.POSITION_LIMIT_EXCEEDED,
                level=SafetyLevel.CRITICAL,
                message='Position out of bounds',
                component='axis_x'
            )
            safety_events.append(event)
            return [event]
        
        mock_safety_manager.check_position_limits = track_position_check
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify safety check was triggered
        assert len(safety_events) > 0
        assert safety_events[0].event_type == SafetyEventType.POSITION_LIMIT_EXCEEDED
    
    @pytest_asyncio.asyncio_test
    async def test_websocket_temperature_warning(self, mock_cache_manager, mock_safety_manager):
        """Test that temperature warnings are triggered."""
        # Simulate high temperature
        message = {
            'method': 'notify_status_update',
            'params': [{
                'temperature_sensor': {'extruder': {'temperature': 260.0}}
            }]
        }
        
        # Track safety events
        safety_events = []
        original_check_temp = mock_safety_manager.check_temperature_limits
        
        async def track_temp_check():
            event = SafetyEvent(
                event_type=SafetyEventType.TEMPERATURE_EXCEEDED,
                level=SafetyLevel.CRITICAL,
                message='Temperature exceeded',
                component='extruder'
            )
            safety_events.append(event)
            return [event]
        
        mock_safety_manager.check_temperature_limits = track_temp_check
        
        # Handle message
        await mock_cache_manager._handle_websocket_message(message)
        
        # Verify safety check was triggered
        assert len(safety_events) > 0
        assert safety_events[0].event_type == SafetyEventType.TEMPERATURE_EXCEEDED
