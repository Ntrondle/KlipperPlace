#!/usr/bin/env python3
# WebSocket Notifier Component for Moonraker
# Provides custom WebSocket notification capabilities for KlipperPlace

import logging
import asyncio
import time
from typing import Dict, Any, Optional, Set, List

# Moonraker imports
from moonraker import Server

# Component logging
logger = logging.getLogger(__name__)


class WebSocketNotifier:
    """Moonraker component for managing WebSocket notifications."""
    
    # Supported event types
    SUPPORTED_EVENTS = [
        'gpio_state_change',
        'fan_speed_change',
        'pwm_value_change',
        'sensor_threshold_alert',
        'position_update',
        'pnp_operation'
    ]
    
    def __init__(self, config: Any) -> None:
        """Initialize the WebSocket Notifier component.
        
        Args:
            config: Moonraker configuration object
        """
        self.server = config.get_server()
        
        # Read configuration
        self.enabled_events = self._parse_enabled_events(config)
        self.throttle_ms = config.getint('throttle_ms', 100, minval=10, maxval=5000)
        self.position_update_rate = config.getint('position_update_rate', 50, minval=10, maxval=500)
        
        # Subscription management
        self._subscribers: Dict[str, Set[int]] = {}
        self._last_notification_time: Dict[str, float] = {}
        self._notification_buffer: Dict[str, Dict[str, Any]] = {}
        
        # Position update task
        self._position_update_task: Optional[asyncio.Task] = None
        self._position_update_enabled = 'position_update' in self.enabled_events
        
        # Register REST endpoints
        self.server.register_endpoint(
            "/api/websocket_notifier/subscribe",
            ['POST'],
            self._handle_subscribe
        )
        
        self.server.register_endpoint(
            "/api/websocket_notifier/unsubscribe",
            ['POST'],
            self._handle_unsubscribe
        )
        
        self.server.register_endpoint(
            "/api/websocket_notifier/subscriptions",
            ['GET'],
            self._handle_get_subscriptions
        )
        
        # Register event handlers for Moonraker events
        self._register_moonraker_event_handlers()
        
        # Start position update task if enabled
        if self._position_update_enabled:
            self._position_update_task = self.server.get_event_loop().create_task(
                self._position_update_loop()
            )
        
        logger.info(f"WebSocket Notifier initialized with {len(self.enabled_events)} enabled events: "
                   f"{self.enabled_events}, throttle_ms={self.throttle_ms}")
    
    def _parse_enabled_events(self, config: Any) -> List[str]:
        """Parse enabled events from configuration.
        
        Args:
            config: Moonraker configuration object
            
        Returns:
            List of enabled event names
        """
        events_str = config.get('enabled_events', '')
        if not events_str:
            # Enable all events by default
            logger.info("No specific events configured, enabling all supported events")
            return self.SUPPORTED_EVENTS.copy()
        
        # Parse comma-separated list
        events = [event.strip() for event in events_str.split(',') if event.strip()]
        
        # Validate events
        invalid_events = [e for e in events if e not in self.SUPPORTED_EVENTS]
        if invalid_events:
            logger.warning(f"Invalid events configured and will be ignored: {invalid_events}")
            events = [e for e in events if e in self.SUPPORTED_EVENTS]
        
        logger.info(f"Configured enabled events: {events}")
        return events
    
    def _register_moonraker_event_handlers(self) -> None:
        """Register handlers for Moonraker events that we want to forward."""
        # Register for Klippy status updates
        self.server.register_event_handler(
            "klippy:status_update",
            self._on_klippy_status_update
        )
        
        # Register for G-code responses
        self.server.register_event_handler(
            "klippy:gcode_response",
            self._on_gcode_response
        )
        
        # Register for Klippy ready state
        self.server.register_event_handler(
            "klippy:ready",
            self._on_klippy_ready
        )
        
        # Register for Klippy shutdown
        self.server.register_event_handler(
            "klippy:shutdown",
            self._on_klippy_shutdown
        )
        
        logger.info("Registered Moonraker event handlers")
    
    async def _handle_subscribe(self, web_request: Any) -> Dict[str, Any]:
        """Handle POST request to subscribe to notifications.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing subscription result
        """
        try:
            # Get client connection
            client_conn = web_request.get_client_connection()
            if client_conn is None:
                return {
                    'success': False,
                    'error': 'No active WebSocket connection'
                }
            
            client_id = client_conn.uid
            
            # Get events to subscribe to
            events = web_request.get_list('events', [])
            
            if not events:
                # Subscribe to all enabled events
                events = self.enabled_events
            
            # Validate events
            invalid_events = [e for e in events if e not in self.enabled_events]
            if invalid_events:
                logger.warning(f"Attempted to subscribe to invalid events: {invalid_events}")
                events = [e for e in events if e in self.enabled_events]
            
            # Add to subscriptions
            for event in events:
                if event not in self._subscribers:
                    self._subscribers[event] = set()
                self._subscribers[event].add(client_id)
            
            logger.info(f"Client {client_id} subscribed to events: {events}")
            
            return {
                'success': True,
                'client_id': client_id,
                'subscribed_events': events,
                'available_events': self.enabled_events
            }
            
        except Exception as e:
            logger.error(f"Error handling subscription request: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _handle_unsubscribe(self, web_request: Any) -> Dict[str, Any]:
        """Handle POST request to unsubscribe from notifications.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing unsubscription result
        """
        try:
            # Get client connection
            client_conn = web_request.get_client_connection()
            if client_conn is None:
                return {
                    'success': False,
                    'error': 'No active WebSocket connection'
                }
            
            client_id = client_conn.uid
            
            # Get events to unsubscribe from
            events = web_request.get_list('events', [])
            
            if not events:
                # Unsubscribe from all events
                events = list(self._subscribers.keys())
            
            # Remove from subscriptions
            unsubscribed_events = []
            for event in events:
                if event in self._subscribers and client_id in self._subscribers[event]:
                    self._subscribers[event].remove(client_id)
                    unsubscribed_events.append(event)
                    
                    # Clean up empty subscription sets
                    if not self._subscribers[event]:
                        del self._subscribers[event]
            
            logger.info(f"Client {client_id} unsubscribed from events: {unsubscribed_events}")
            
            return {
                'success': True,
                'client_id': client_id,
                'unsubscribed_events': unsubscribed_events
            }
            
        except Exception as e:
            logger.error(f"Error handling unsubscription request: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _handle_get_subscriptions(self, web_request: Any) -> Dict[str, Any]:
        """Handle GET request to get current subscriptions.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing current subscriptions
        """
        try:
            # Get client connection
            client_conn = web_request.get_client_connection()
            if client_conn is None:
                return {
                    'success': False,
                    'error': 'No active WebSocket connection'
                }
            
            client_id = client_conn.uid
            
            # Get events this client is subscribed to
            subscribed_events = [
                event for event, subscribers in self._subscribers.items()
                if client_id in subscribers
            ]
            
            return {
                'success': True,
                'client_id': client_id,
                'subscribed_events': subscribed_events,
                'available_events': self.enabled_events,
                'total_subscribers': {
                    event: len(subscribers)
                    for event, subscribers in self._subscribers.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting subscriptions: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _on_klippy_status_update(self, status: Dict[str, Any]) -> None:
        """Handle Klippy status update event.
        
        Args:
            status: Klippy status dictionary
        """
        # Extract GPIO state changes
        if 'output_pin' in status and 'gpio_state_change' in self.enabled_events:
            self._send_notification('gpio_state_change', {
                'pins': status['output_pin'],
                'timestamp': time.time()
            })
        
        # Extract fan speed changes
        if 'fan' in status and 'fan_speed_change' in self.enabled_events:
            self._send_notification('fan_speed_change', {
                'fan': status['fan'],
                'timestamp': time.time()
            })
        
        # Extract PWM value changes
        if 'output_pin' in status and 'pwm_value_change' in self.enabled_events:
            pwm_changes = {}
            for pin_name, pin_data in status['output_pin'].items():
                if pin_data.get('is_pwm', False):
                    pwm_changes[pin_name] = {
                        'value': pin_data.get('value', 0),
                        'scale': pin_data.get('scale', 1.0)
                    }
            
            if pwm_changes:
                self._send_notification('pwm_value_change', {
                    'pwm_pins': pwm_changes,
                    'timestamp': time.time()
                })
    
    def _on_gcode_response(self, response: str) -> None:
        """Handle G-code response event.
        
        Args:
            response: G-code response string
        """
        # Could be used to detect PnP operation completions
        if 'pnp_operation' in self.enabled_events:
            # Parse response for PnP-specific information
            if any(keyword in response.lower() for keyword in ['pick', 'place', 'move']):
                self._send_notification('pnp_operation', {
                    'response': response,
                    'timestamp': time.time()
                })
    
    def _on_klippy_ready(self) -> None:
        """Handle Klippy ready event."""
        self._send_notification('system', {
            'event': 'klippy_ready',
            'timestamp': time.time()
        })
    
    def _on_klippy_shutdown(self) -> None:
        """Handle Klippy shutdown event."""
        self._send_notification('system', {
            'event': 'klippy_shutdown',
            'timestamp': time.time()
        })
    
    def _send_notification(self, event_type: str, data: Dict[str, Any]) -> None:
        """Send a notification to subscribed clients with throttling.
        
        Args:
            event_type: Type of notification event
            data: Notification data
        """
        # Check if event is enabled
        if event_type not in self.enabled_events:
            return
        
        # Check if anyone is subscribed to this event
        if event_type not in self._subscribers or not self._subscribers[event_type]:
            return
        
        # Check throttle
        current_time = time.time()
        last_time = self._last_notification_time.get(event_type, 0)
        elapsed_ms = (current_time - last_time) * 1000
        
        if elapsed_ms < self.throttle_ms:
            # Buffer the notification
            self._notification_buffer[event_type] = data
            return
        
        # Send the notification
        self._last_notification_time[event_type] = current_time
        
        # Build notification message
        notification = {
            'jsonrpc': '2.0',
            'method': f'notify_{event_type}',
            'params': [data]
        }
        
        # Send to subscribed clients
        wsm = self.server.lookup_component('websockets')
        for client_id in self._subscribers[event_type]:
            client = wsm.get_client(client_id)
            if client and not client.need_auth:
                client.queue_message(notification)
        
        logger.debug(f"Sent {event_type} notification to {len(self._subscribers[event_type])} clients")
    
    async def _position_update_loop(self) -> None:
        """Background task for high-frequency position updates."""
        try:
            klippy_apis = self.server.lookup_component('klippy_apis')
            
            while True:
                try:
                    # Query current position
                    result = await klippy_apis.query_objects({'toolhead': None})
                    
                    if 'result' in result and 'toolhead' in result['result']:
                        toolhead = result['result']['toolhead']
                        position_data = {
                            'position': toolhead.get('position', [0, 0, 0, 0]),
                            'homed_axes': toolhead.get('homed_axes', ''),
                            'extruder': toolhead.get('extruder', ''),
                            'speed': toolhead.get('speed', 0),
                            'accel': toolhead.get('accel', 0),
                            'max_velocity': toolhead.get('max_velocity', 0),
                            'max_accel': toolhead.get('max_accel', 0),
                            'timestamp': time.time()
                        }
                        
                        # Send position update
                        self._send_notification('position_update', position_data)
                    
                    # Wait for next update
                    await asyncio.sleep(self.position_update_rate / 1000.0)
                    
                except Exception as e:
                    logger.error(f"Error in position update loop: {e}")
                    await asyncio.sleep(1.0)
                    
        except asyncio.CancelledError:
            logger.info("Position update loop cancelled")
            raise
    
    def notify_gpio_change(self, pin_name: str, value: float, is_pwm: bool = False) -> None:
        """Send a GPIO state change notification.
        
        Args:
            pin_name: Name of the GPIO pin
            value: Current value of the pin
            is_pwm: Whether this is a PWM pin
        """
        if 'gpio_state_change' not in self.enabled_events:
            return
        
        self._send_notification('gpio_state_change', {
            'pin_name': pin_name,
            'value': value,
            'is_pwm': is_pwm,
            'timestamp': time.time()
        })
    
    def notify_fan_change(self, fan_name: str, speed: float, rpm: int = 0) -> None:
        """Send a fan speed change notification.
        
        Args:
            fan_name: Name of the fan
            speed: Fan speed (0.0 to 1.0)
            rpm: Current RPM (if available)
        """
        if 'fan_speed_change' not in self.enabled_events:
            return
        
        self._send_notification('fan_speed_change', {
            'fan_name': fan_name,
            'speed': speed,
            'rpm': rpm,
            'timestamp': time.time()
        })
    
    def notify_pwm_change(self, pin_name: str, value: float, scale: float = 1.0) -> None:
        """Send a PWM value change notification.
        
        Args:
            pin_name: Name of the PWM pin
            value: Current PWM value
            scale: PWM scale factor
        """
        if 'pwm_value_change' not in self.enabled_events:
            return
        
        self._send_notification('pwm_value_change', {
            'pin_name': pin_name,
            'value': value,
            'scale': scale,
            'timestamp': time.time()
        })
    
    def notify_sensor_alert(self, sensor_name: str, value: float, 
                           threshold: float, condition: str) -> None:
        """Send a sensor threshold alert notification.
        
        Args:
            sensor_name: Name of the sensor
            value: Current sensor value
            threshold: Threshold value
            condition: Condition that triggered the alert ('above', 'below', 'equal')
        """
        if 'sensor_threshold_alert' not in self.enabled_events:
            return
        
        self._send_notification('sensor_threshold_alert', {
            'sensor_name': sensor_name,
            'value': value,
            'threshold': threshold,
            'condition': condition,
            'timestamp': time.time()
        })
    
    def notify_pnp_operation(self, operation_type: str, status: str, 
                            details: Optional[Dict[str, Any]] = None) -> None:
        """Send a PnP operation notification.
        
        Args:
            operation_type: Type of operation ('pick', 'place', 'move', etc.)
            status: Status of the operation ('started', 'completed', 'failed')
            details: Optional additional details about the operation
        """
        if 'pnp_operation' not in self.enabled_events:
            return
        
        notification_data = {
            'operation_type': operation_type,
            'status': status,
            'timestamp': time.time()
        }
        
        if details:
            notification_data['details'] = details
        
        self._send_notification('pnp_operation', notification_data)
    
    def get_status(self, eventtime: float) -> Dict[str, Any]:
        """Get component status for Moonraker status reporting.
        
        Args:
            eventtime: Current event time
            
        Returns:
            Dictionary containing component status
        """
        subscriber_count = sum(len(subs) for subs in self._subscribers.values())
        
        return {
            'enabled_events': self.enabled_events,
            'throttle_ms': self.throttle_ms,
            'position_update_rate': self.position_update_rate,
            'total_subscribers': subscriber_count,
            'subscriptions': {
                event: len(subscribers)
                for event, subscribers in self._subscribers.items()
            },
            'component': 'websocket_notifier'
        }
    
    def close(self) -> None:
        """Cleanup when component is closed."""
        # Cancel position update task if running
        if self._position_update_task and not self._position_update_task.done():
            self._position_update_task.cancel()
        
        # Clear subscriptions
        self._subscribers.clear()
        self._last_notification_time.clear()
        self._notification_buffer.clear()
        
        logger.info("WebSocket Notifier component closed")


def load_component(config: Any) -> WebSocketNotifier:
    """Load the WebSocket Notifier component.
    
    This function is called by Moonraker to load the component.
    
    Args:
        config: Moonraker configuration object
        
    Returns:
        Instance of WebSocketNotifier component
    """
    return WebSocketNotifier(config)
