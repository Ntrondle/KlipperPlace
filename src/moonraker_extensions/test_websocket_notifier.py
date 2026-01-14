#!/usr/bin/env python3
# Unit tests for WebSocket Notifier component

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock


class WebSocketNotifier:
    """Mock WebSocketNotifier class for testing."""
    
    def __init__(self, config):
        self.server = config.get_server()
        self.enabled_events = []
        self.throttle_ms = 100
        self.position_update_rate = 50
        self._subscribers = {}
        self._last_notification_time = {}
        self._notification_buffer = {}
        self._position_update_task = None
        self._position_update_enabled = False


@pytest.fixture
def mock_server():
    """Create a mock Moonraker server."""
    server = Mock()
    server.lookup_component = Mock()
    server.register_endpoint = Mock()
    server.register_event_handler = Mock()
    server.get_event_loop = Mock()
    return server


@pytest.fixture
def mock_config(mock_server):
    """Create a mock config object."""
    config = Mock()
    config.get_server = Mock(return_value=mock_server)
    config.getint = Mock(side_effect=lambda key, default=100, minval=10, maxval=5000: default)
    config.get = Mock(return_value='')
    return config


@pytest.fixture
def websocket_notifier(mock_config):
    """Create a WebSocketNotifier instance for testing."""
    mock_server = mock_config.get_server()
    
    notifier = WebSocketNotifier(mock_config)
    return notifier


class TestWebSocketNotifierInitialization:
    """Test WebSocketNotifier initialization."""
    
    def test_initialization_with_defaults(self, mock_config):
        """Test initialization with default configuration."""
        mock_server = mock_config.get_server()
        
        notifier = WebSocketNotifier(mock_config)
        
        assert notifier.server is not None
        assert notifier.enabled_events == []
        assert notifier.throttle_ms == 100
        assert notifier.position_update_rate == 50
        assert notifier._subscribers == {}
        assert notifier._last_notification_time == {}
        assert notifier._notification_buffer == {}
    
    def test_initialization_with_custom_values(self, mock_config):
        """Test initialization with custom values."""
        mock_server = mock_config.get_server()
        mock_config.getint = Mock(side_effect=lambda key, default=100, minval=10, maxval=5000: 200 if key == 'throttle_ms' else 100)
        mock_config.get = Mock(return_value='gpio_state_change,fan_speed_change')
        
        notifier = WebSocketNotifier(mock_config)
        
        assert notifier.throttle_ms == 200
        assert notifier.enabled_events == ['gpio_state_change', 'fan_speed_change']
    
    def test_initialization_with_all_events_enabled(self, mock_config):
        """Test initialization with all events enabled (default)."""
        mock_server = mock_config.get_server()
        mock_config.get = Mock(return_value='')
        
        notifier = WebSocketNotifier(mock_config)
        
        # When no events specified, all should be enabled
        assert len(notifier.enabled_events) > 0
    
    def test_endpoint_registration(self, mock_config):
        """Test that REST endpoints are registered."""
        mock_server = mock_config.get_server()
        
        WebSocketNotifier(mock_config)
        
        assert mock_server.register_endpoint.call_count == 3
        calls = mock_server.register_endpoint.call_args_list
        
        # Check endpoints
        endpoints = [call[0][0] for call in calls]
        assert '/api/websocket_notifier/subscribe' in endpoints
        assert '/api/websocket_notifier/unsubscribe' in endpoints
        assert '/api/websocket_notifier/subscriptions' in endpoints
    
    def test_event_handler_registration(self, mock_config):
        """Test that Moonraker event handlers are registered."""
        mock_server = mock_config.get_server()
        
        WebSocketNotifier(mock_config)
        
        assert mock_server.register_event_handler.call_count == 4


class TestParseEnabledEvents:
    """Test parsing of enabled events configuration."""
    
    def test_parse_empty_events(self, mock_config):
        """Test parsing empty events (should enable all)."""
        mock_server = mock_config.get_server()
        mock_config.get = Mock(return_value='')
        
        notifier = WebSocketNotifier(mock_config)
        
        # Should enable all supported events
        assert len(notifier.enabled_events) > 0
    
    def test_parse_single_event(self, mock_config):
        """Test parsing single enabled event."""
        mock_server = mock_config.get_server()
        mock_config.get = Mock(return_value='gpio_state_change')
        
        notifier = WebSocketNotifier(mock_config)
        
        assert notifier.enabled_events == ['gpio_state_change']
    
    def test_parse_multiple_events(self, mock_config):
        """Test parsing multiple enabled events."""
        mock_server = mock_config.get_server()
        mock_config.get = Mock(return_value='gpio_state_change,fan_speed_change,pwm_value_change')
        
        notifier = WebSocketNotifier(mock_config)
        
        assert 'gpio_state_change' in notifier.enabled_events
        assert 'fan_speed_change' in notifier.enabled_events
        assert 'pwm_value_change' in notifier.enabled_events
    
    def test_parse_events_with_invalid_event(self, mock_config):
        """Test parsing events with invalid event (should be filtered)."""
        mock_server = mock_config.get_server()
        mock_config.get = Mock(return_value='gpio_state_change,invalid_event,fan_speed_change')
        
        notifier = WebSocketNotifier(mock_config)
        
        assert 'gpio_state_change' in notifier.enabled_events
        assert 'fan_speed_change' in notifier.enabled_events
        assert 'invalid_event' not in notifier.enabled_events


class TestHandleSubscribe:
    """Test subscription handler."""
    
    @pytest.mark.asyncio
    async def test_subscribe_success(self, websocket_notifier):
        """Test successful subscription."""
        websocket_notifier.enabled_events = ['gpio_state_change', 'fan_speed_change']
        
        client_conn = Mock()
        client_conn.uid = 'client_123'
        
        web_request = Mock()
        web_request.get_client_connection = Mock(return_value=client_conn)
        web_request.get_list = Mock(return_value=['gpio_state_change'])
        
        result = await websocket_notifier._handle_subscribe(web_request)
        
        assert result['success'] == True
        assert result['client_id'] == 'client_123'
        assert 'gpio_state_change' in result['subscribed_events']
        assert 'client_123' in websocket_notifier._subscribers['gpio_state_change']
    
    @pytest.mark.asyncio
    async def test_subscribe_to_all_events(self, websocket_notifier):
        """Test subscribing to all enabled events."""
        websocket_notifier.enabled_events = ['gpio_state_change', 'fan_speed_change']
        
        client_conn = Mock()
        client_conn.uid = 'client_456'
        
        web_request = Mock()
        web_request.get_client_connection = Mock(return_value=client_conn)
        web_request.get_list = Mock(return_value=[])
        
        result = await websocket_notifier._handle_subscribe(web_request)
        
        assert result['success'] == True
        assert len(result['subscribed_events']) == 2
    
    @pytest.mark.asyncio
    async def test_subscribe_with_invalid_events(self, websocket_notifier):
        """Test subscribing with invalid events (should be filtered)."""
        websocket_notifier.enabled_events = ['gpio_state_change']
        
        client_conn = Mock()
        client_conn.uid = 'client_789'
        
        web_request = Mock()
        web_request.get_client_connection = Mock(return_value=client_conn)
        web_request.get_list = Mock(return_value=['gpio_state_change', 'invalid_event'])
        
        result = await websocket_notifier._handle_subscribe(web_request)
        
        assert result['success'] == True
        assert 'gpio_state_change' in result['subscribed_events']
        assert 'invalid_event' not in result['subscribed_events']
    
    @pytest.mark.asyncio
    async def test_subscribe_no_connection(self, websocket_notifier):
        """Test subscription with no WebSocket connection."""
        web_request = Mock()
        web_request.get_client_connection = Mock(return_value=None)
        
        result = await websocket_notifier._handle_subscribe(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'No active WebSocket connection' in result['error']


class TestHandleUnsubscribe:
    """Test unsubscription handler."""
    
    @pytest.mark.asyncio
    async def test_unsubscribe_success(self, websocket_notifier):
        """Test successful unsubscription."""
        # Add subscription first
        websocket_notifier._subscribers['gpio_state_change'] = {'client_123', 'client_456'}
        
        client_conn = Mock()
        client_conn.uid = 'client_123'
        
        web_request = Mock()
        web_request.get_client_connection = Mock(return_value=client_conn)
        web_request.get_list = Mock(return_value=['gpio_state_change'])
        
        result = await websocket_notifier._handle_unsubscribe(web_request)
        
        assert result['success'] == True
        assert result['client_id'] == 'client_123'
        assert 'gpio_state_change' in result['unsubscribed_events']
        assert 'client_123' not in websocket_notifier._subscribers['gpio_state_change']
    
    @pytest.mark.asyncio
    async def test_unsubscribe_from_all_events(self, websocket_notifier):
        """Test unsubscribing from all events."""
        # Add subscriptions
        websocket_notifier._subscribers['gpio_state_change'] = {'client_123'}
        websocket_notifier._subscribers['fan_speed_change'] = {'client_123'}
        
        client_conn = Mock()
        client_conn.uid = 'client_123'
        
        web_request = Mock()
        web_request.get_client_connection = Mock(return_value=client_conn)
        web_request.get_list = Mock(return_value=[])
        
        result = await websocket_notifier._handle_unsubscribe(web_request)
        
        assert result['success'] == True
        assert len(result['unsubscribed_events']) == 2
    
    @pytest.mark.asyncio
    async def test_unsubscribe_no_connection(self, websocket_notifier):
        """Test unsubscription with no WebSocket connection."""
        web_request = Mock()
        web_request.get_client_connection = Mock(return_value=None)
        
        result = await websocket_notifier._handle_unsubscribe(web_request)
        
        assert result['success'] == False
        assert 'error' in result


class TestHandleGetSubscriptions:
    """Test get subscriptions handler."""
    
    @pytest.mark.asyncio
    async def test_get_subscriptions_success(self, websocket_notifier):
        """Test successful get subscriptions."""
        # Add subscriptions
        websocket_notifier._subscribers['gpio_state_change'] = {'client_123', 'client_456'}
        websocket_notifier._subscribers['fan_speed_change'] = {'client_123'}
        
        client_conn = Mock()
        client_conn.uid = 'client_123'
        
        web_request = Mock()
        web_request.get_client_connection = Mock(return_value=client_conn)
        
        result = await websocket_notifier._handle_get_subscriptions(web_request)
        
        assert result['success'] == True
        assert result['client_id'] == 'client_123'
        assert 'gpio_state_change' in result['subscribed_events']
        assert 'fan_speed_change' in result['subscribed_events']
        assert result['total_subscribers']['gpio_state_change'] == 2
        assert result['total_subscribers']['fan_speed_change'] == 1
    
    @pytest.mark.asyncio
    async def test_get_subscriptions_no_connection(self, websocket_notifier):
        """Test get subscriptions with no WebSocket connection."""
        web_request = Mock()
        web_request.get_client_connection = Mock(return_value=None)
        
        result = await websocket_notifier._handle_get_subscriptions(web_request)
        
        assert result['success'] == False
        assert 'error' in result


class TestSendNotification:
    """Test notification sending."""
    
    def test_send_notification_success(self, websocket_notifier):
        """Test successful notification sending."""
        websocket_notifier.enabled_events = ['gpio_state_change']
        websocket_notifier._subscribers['gpio_state_change'] = {'client_123', 'client_456'}
        websocket_notifier._last_notification_time['gpio_state_change'] = 0.0
        
        # Mock WebSocket manager
        wsm = Mock()
        client = Mock()
        client.need_auth = False
        client.queue_message = Mock()
        wsm.get_client = Mock(return_value=client)
        
        # Send notification
        websocket_notifier.server.lookup_component = Mock(return_value=wsm)
        
        websocket_notifier._send_notification('gpio_state_change', {'pin': 'PIN1', 'value': 1})
        
        # Verify notification was queued
        assert client.queue_message.called
        assert 'gpio_state_change' in websocket_notifier._last_notification_time
    
    def test_send_notification_disabled_event(self, websocket_notifier):
        """Test notification for disabled event."""
        websocket_notifier.enabled_events = ['fan_speed_change']
        websocket_notifier._subscribers['gpio_state_change'] = {'client_123'}
        
        # Should not send notification
        websocket_notifier._send_notification('gpio_state_change', {'pin': 'PIN1', 'value': 1})
        
        # Verify notification was NOT sent
        assert 'gpio_state_change' not in websocket_notifier._last_notification_time
    
    def test_send_notification_no_subscribers(self, websocket_notifier):
        """Test notification with no subscribers."""
        websocket_notifier.enabled_events = ['gpio_state_change']
        websocket_notifier._subscribers['gpio_state_change'] = set()
        
        # Should not send notification
        websocket_notifier._send_notification('gpio_state_change', {'pin': 'PIN1', 'value': 1})
        
        # Verify notification was NOT sent
        assert 'gpio_state_change' not in websocket_notifier._last_notification_time
    
    def test_send_notification_throttled(self, websocket_notifier):
        """Test notification throttling."""
        websocket_notifier.enabled_events = ['gpio_state_change']
        websocket_notifier._subscribers['gpio_state_change'] = {'client_123'}
        websocket_notifier.throttle_ms = 100
        
        # Set recent notification time
        websocket_notifier._last_notification_time['gpio_state_change'] = 1000.0
        
        # Try to send notification immediately (should be throttled)
        websocket_notifier._send_notification('gpio_state_change', {'pin': 'PIN1', 'value': 1})
        
        # Verify notification was buffered
        assert 'gpio_state_change' in websocket_notifier._notification_buffer


class TestNotifyMethods:
    """Test notification helper methods."""
    
    def test_notify_gpio_change(self, websocket_notifier):
        """Test GPIO change notification."""
        websocket_notifier.enabled_events = ['gpio_state_change']
        
        # Mock send_notification
        original_send = websocket_notifier._send_notification
        websocket_notifier._send_notification = Mock()
        
        websocket_notifier.notify_gpio_change('PIN1', 1.0, False)
        
        assert websocket_notifier._send_notification.called
        call_args = websocket_notifier._send_notification.call_args
        assert call_args[0][0] == 'gpio_state_change'
        assert call_args[0][1]['pin_name'] == 'PIN1'
        assert call_args[0][1]['value'] == 1.0
        
        # Restore
        websocket_notifier._send_notification = original_send
    
    def test_notify_fan_change(self, websocket_notifier):
        """Test fan change notification."""
        websocket_notifier.enabled_events = ['fan_speed_change']
        
        # Mock send_notification
        original_send = websocket_notifier._send_notification
        websocket_notifier._send_notification = Mock()
        
        websocket_notifier.notify_fan_change('fan', 0.75, 1500)
        
        assert websocket_notifier._send_notification.called
        call_args = websocket_notifier._send_notification.call_args
        assert call_args[0][0] == 'fan_speed_change'
        assert call_args[0][1]['fan_name'] == 'fan'
        assert call_args[0][1]['speed'] == 0.75
        assert call_args[0][1]['rpm'] == 1500
        
        # Restore
        websocket_notifier._send_notification = original_send
    
    def test_notify_pwm_change(self, websocket_notifier):
        """Test PWM change notification."""
        websocket_notifier.enabled_events = ['pwm_value_change']
        
        # Mock send_notification
        original_send = websocket_notifier._send_notification
        websocket_notifier._send_notification = Mock()
        
        websocket_notifier.notify_pwm_change('PWM_PIN', 0.5, 1.0)
        
        assert websocket_notifier._send_notification.called
        call_args = websocket_notifier._send_notification.call_args
        assert call_args[0][0] == 'pwm_value_change'
        assert call_args[0][1]['pin_name'] == 'PWM_PIN'
        assert call_args[0][1]['value'] == 0.5
        assert call_args[0][1]['scale'] == 1.0
        
        # Restore
        websocket_notifier._send_notification = original_send
    
    def test_notify_sensor_alert(self, websocket_notifier):
        """Test sensor alert notification."""
        websocket_notifier.enabled_events = ['sensor_threshold_alert']
        
        # Mock send_notification
        original_send = websocket_notifier._send_notification
        websocket_notifier._send_notification = Mock()
        
        websocket_notifier.notify_sensor_alert('temp_sensor', 100.0, 95.0, 'above')
        
        assert websocket_notifier._send_notification.called
        call_args = websocket_notifier._send_notification.call_args
        assert call_args[0][0] == 'sensor_threshold_alert'
        assert call_args[0][1]['sensor_name'] == 'temp_sensor'
        assert call_args[0][1]['value'] == 100.0
        assert call_args[0][1]['threshold'] == 95.0
        assert call_args[0][1]['condition'] == 'above'
        
        # Restore
        websocket_notifier._send_notification = original_send
    
    def test_notify_pnp_operation(self, websocket_notifier):
        """Test PnP operation notification."""
        websocket_notifier.enabled_events = ['pnp_operation']
        
        # Mock send_notification
        original_send = websocket_notifier._send_notification
        websocket_notifier._send_notification = Mock()
        
        websocket_notifier.notify_pnp_operation('pick', 'completed', {'component': 'vacuum'})
        
        assert websocket_notifier._send_notification.called
        call_args = websocket_notifier._send_notification.call_args
        assert call_args[0][0] == 'pnp_operation'
        assert call_args[0][1]['operation_type'] == 'pick'
        assert call_args[0][1]['status'] == 'completed'
        assert call_args[0][1]['details']['component'] == 'vacuum'
        
        # Restore
        websocket_notifier._send_notification = original_send


class TestGetStatus:
    """Test get_status method."""
    
    def test_get_status(self, websocket_notifier):
        """Test getting component status."""
        websocket_notifier.enabled_events = ['gpio_state_change', 'fan_speed_change']
        websocket_notifier._subscribers['gpio_state_change'] = {'client_123', 'client_456'}
        websocket_notifier._subscribers['fan_speed_change'] = {'client_789'}
        
        status = websocket_notifier.get_status(123456.789)
        
        assert status['enabled_events'] == ['gpio_state_change', 'fan_speed_change']
        assert status['throttle_ms'] == 100
        assert status['position_update_rate'] == 50
        assert status['total_subscribers'] == 3
        assert status['subscriptions']['gpio_state_change'] == 2
        assert status['subscriptions']['fan_speed_change'] == 1


class TestClose:
    """Test close method."""
    
    def test_close(self, websocket_notifier):
        """Test closing component."""
        # Add active task
        task = Mock()
        task.done = Mock(return_value=False)
        websocket_notifier._position_update_task = task
        
        websocket_notifier.close()
        
        # Verify task was cancelled
        assert task.cancel.called
        assert len(websocket_notifier._subscribers) == 0
        assert len(websocket_notifier._last_notification_time) == 0
        assert len(websocket_notifier._notification_buffer) == 0


class TestLoadComponent:
    """Test load_component function."""
    
    def test_load_component(self, mock_config):
        """Test loading component via load_component function."""
        from moonraker_extensions.websocket_notifier import load_component
        
        mock_server = mock_config.get_server()
        
        notifier = load_component(mock_config)
        
        assert isinstance(notifier, WebSocketNotifier)
        assert notifier.server is not None
