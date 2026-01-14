#!/usr/bin/env python3
# Unit tests for Actuator, Vacuum, Fan, PWM, GPIO, Sensor, Feeder, Status, Queue, System, Batch, and Version Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
    server.safety_manager = Mock()
    server.safety_manager.validate_fan_command = AsyncMock(return_value=(True, []))
    server.safety_manager.validate_move_command = AsyncMock(return_value=(True, []))
    server.safety_manager.mark_axis_homed = Mock()
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


class TestActuatorRoutes:
    """Test actuator route handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_actuate_success(self, mock_server, mock_request):
        """Test successful actuate command."""
        from api.routes.actuator_routes import handle_actuate
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'pin': 'ACT1', 'value': 1.0}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="ACTUATE ACT1 VALUE=1.0"
        )
        
        response = await handle_actuate(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_actuate_missing_pin(self, mock_server, mock_request):
        """Test actuate with missing pin."""
        from api.routes.actuator_routes import handle_actuate
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'value': 1.0}
        
        response = await handle_actuate(mock_request)
        
        assert response.status == 400
        data = await response.json()
        assert data['error_code'] == 'MISSING_PARAMETER'
    
    @pytest.mark.asyncio
    async def test_handle_actuate_exception(self, mock_server, mock_request):
        """Test actuate with exception."""
        from api.routes.actuator_routes import handle_actuate
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'pin': 'ACT1', 'value': 1.0}
        
        mock_server.execute_command = AsyncMock(side_effect=Exception('Failed'))
        
        response = await handle_actuate(mock_request)
        
        assert response.status == 500
        data = await response.json()
        assert data['error_code'] == 'EXECUTION_ERROR'


class TestVacuumRoutes:
    """Test vacuum route handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_on_success(self, mock_server, mock_request):
        """Test successful vacuum on command."""
        from api.routes.vacuum_routes import handle_vacuum_on
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'power': 200}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="VACUUM_ON P200"
        )
        
        response = await handle_vacuum_on(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_on_invalid_power(self, mock_server, mock_request):
        """Test vacuum on with invalid power."""
        from api.routes.vacuum_routes import handle_vacuum_on
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'power': 300}
        
        response = await handle_vacuum_on(mock_request)
        
        assert response.status == 400
        data = await response.json()
        assert data['error_code'] == 'INVALID_PARAMETER'
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_off_success(self, mock_server, mock_request):
        """Test successful vacuum off command."""
        from api.routes.vacuum_routes import handle_vacuum_off
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="VACUUM_OFF"
        )
        
        response = await handle_vacuum_off(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_set_success(self, mock_server, mock_request):
        """Test successful vacuum set command."""
        from api.routes.vacuum_routes import handle_vacuum_set
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'power': 150}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="VACUUM_SET P150"
        )
        
        response = await handle_vacuum_set(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_set_missing_power(self, mock_server, mock_request):
        """Test vacuum set with missing power."""
        from api.routes.vacuum_routes import handle_vacuum_set
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {}
        
        response = await handle_vacuum_set(mock_request)
        
        assert response.status == 400
        data = await response.json()
        assert data['error_code'] == 'MISSING_PARAMETER'


class TestFanRoutes:
    """Test fan route handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_fan_on_success(self, mock_server, mock_request):
        """Test successful fan on command."""
        from api.routes.fan_routes import handle_fan_on
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'fan': 'fan', 'speed': 0.75}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="FAN_ON FAN=0.75"
        )
        
        response = await handle_fan_on(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_fan_on_invalid_speed(self, mock_server, mock_request):
        """Test fan on with invalid speed."""
        from api.routes.fan_routes import handle_fan_on
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'fan': 'fan', 'speed': 1.5}
        
        # Setup safety manager to return violation
        mock_server.safety_manager.validate_fan_command = AsyncMock(
            return_value=(False, ['Speed must be a float between 0.0 and 1.0'])
        )
        
        response = await handle_fan_on(mock_request)
        
        assert response.status == 400
        data = await response.json()
        assert data['error_code'] == 'BOUNDS_VIOLATION'
    
    @pytest.mark.asyncio
    async def test_handle_fan_off_success(self, mock_server, mock_request):
        """Test successful fan off command."""
        from api.routes.fan_routes import handle_fan_off
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'fan': 'fan'}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="FAN_OFF FAN=fan"
        )
        
        response = await handle_fan_off(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_fan_set_success(self, mock_server, mock_request):
        """Test successful fan set command."""
        from api.routes.fan_routes import handle_fan_set
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'fan': 'fan', 'speed': 0.5}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="FAN_SET FAN=0.5"
        )
        
        response = await handle_fan_set(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'


class TestPWMRoutes:
    """Test PWM route handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_pwm_set_success(self, mock_server, mock_request):
        """Test successful PWM set command."""
        from api.routes.pwm_routes import handle_pwm_set
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'pin': 'PWM1', 'value': 0.75}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="SET_PIN PIN=PWM1 VALUE=0.75"
        )
        
        response = await handle_pwm_set(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_pwm_set_missing_pin(self, mock_server, mock_request):
        """Test PWM set with missing pin."""
        from api.routes.pwm_routes import handle_pwm_set
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'value': 0.75}
        
        response = await handle_pwm_set(mock_request)
        
        assert response.status == 400
        data = await response.json()
        assert data['error_code'] == 'MISSING_PARAMETER'
    
    @pytest.mark.asyncio
    async def test_handle_pwm_set_invalid_value(self, mock_server, mock_request):
        """Test PWM set with invalid value."""
        from api.routes.pwm_routes import handle_pwm_set
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'pin': 'PWM1', 'value': 1.5}
        
        response = await handle_pwm_set(mock_request)
        
        assert response.status == 400
        data = await response.json()
        assert data['error_code'] == 'INVALID_PARAMETER'


class TestGPIORoutes:
    """Test GPIO route handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_gpio_read_success(self, mock_server, mock_request):
        """Test successful GPIO read command."""
        from api.routes.gpio_routes import handle_gpio_read
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="GPIO_READ"
        )
        
        response = await handle_gpio_read(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_gpio_write_success(self, mock_server, mock_request):
        """Test successful GPIO write command."""
        from api.routes.gpio_routes import handle_gpio_write
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'pin': 'GPIO1', 'value': 1}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="GPIO_WRITE PIN=GPIO1 VALUE=1"
        )
        
        response = await handle_gpio_write(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'


class TestSensorRoutes:
    """Test sensor route handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_sensor_read_success(self, mock_server, mock_request):
        """Test successful sensor read command."""
        from api.routes.sensor_routes import handle_sensor_read
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="SENSOR_READ"
        )
        
        response = await handle_sensor_read(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_sensor_read_specific(self, mock_server, mock_request):
        """Test sensor read for specific sensor."""
        from api.routes.sensor_routes import handle_sensor_read
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'sensor': 'temp_sensor'}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="SENSOR_READ SENSOR=temp_sensor"
        )
        
        response = await handle_sensor_read(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'


class TestFeederRoutes:
    """Test feeder route handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_feeder_advance_success(self, mock_server, mock_request):
        """Test successful feeder advance command."""
        from api.routes.feeder_routes import handle_feeder_advance
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'distance': 10.0}
        
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="FEEDER_ADVANCE DISTANCE=10.0"
        )
        
        response = await handle_feeder_advance(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'


class TestStatusRoutes:
    """Test status route handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_get_status_success(self, mock_server, mock_request):
        """Test successful get status command."""
        from api.routes.status_routes import handle_get_status
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="STATUS_QUERY",
            response={'status': 'idle', 'position': {'x': 100, 'y': 50, 'z': 10}}
        )
        
        response = await handle_get_status(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'status' in data


class TestQueueRoutes:
    """Test queue route handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_get_queue_success(self, mock_server, mock_request):
        """Test successful get queue command."""
        from api.routes.queue_routes import handle_get_queue
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        
        # Mock queue snapshot
        mock_server.get_queue_status = AsyncMock(return_value={
            'size': 3,
            'snapshot': [
                {'id': 'cmd1', 'command': 'G0 X100', 'priority': 1},
                {'id': 'cmd2', 'command': 'G0 Y100', 'priority': 1},
                {'id': 'cmd3', 'command': 'G0 Z100', 'priority': 1}
            ]
        })
        
        response = await handle_get_queue(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert data['size'] == 3
        assert len(data['snapshot']) == 3
    
    @pytest.mark.asyncio
    async def test_handle_clear_queue_success(self, mock_server, mock_request):
        """Test successful clear queue command."""
        from api.routes.queue_routes import handle_clear_queue
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        
        response = await handle_clear_queue(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'


class TestSystemRoutes:
    """Test system route handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_get_info_success(self, mock_server, mock_request):
        """Test successful get info command."""
        from api.routes.system_routes import handle_get_info
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="SYSTEM_INFO",
            response={'version': '1.0.0', 'uptime': 3600}
        )
        
        response = await handle_get_info(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'version' in data


class TestBatchRoutes:
    """Test batch route handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_execute_batch_success(self, mock_server, mock_request):
        """Test successful execute batch command."""
        from api.routes.batch_routes import handle_execute_batch
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {
            'gcodes': ['G0 X100', 'G0 Y100'],
            'stop_on_error': True
        }
        
        mock_server.execute_batch.return_value = [
            ExecutionResult(status=ExecutionStatus.SUCCESS, gcode='G0 X100'),
            ExecutionResult(status=ExecutionStatus.SUCCESS, gcode='G0 Y100')
        ]
        
        response = await handle_execute_batch(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert len(data['results']) == 2
    
    @pytest.mark.asyncio
    async def test_handle_execute_batch_no_gcodes(self, mock_server, mock_request):
        """Test execute batch with no G-codes."""
        from api.routes.batch_routes import handle_execute_batch
        
        mock_request.app = {'server': mock_server}
        mock_request.json.return_value = {'stop_on_error': True}
        
        response = await handle_execute_batch(mock_request)
        
        assert response.status == 400
        data = await response.json()
        assert data['error_code'] == 'MISSING_PARAMETER'


class TestVersionRoutes:
    """Test version route handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_get_version_success(self, mock_server, mock_request):
        """Test successful get version command."""
        from api.routes.version_routes import handle_get_version
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        
        mock_request.app = {'server': mock_server}
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="VERSION_QUERY",
            response={'version': '1.0.0', 'api_version': '1.0'}
        )
        
        response = await handle_get_version(mock_request)
        
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'version' in data
