#!/usr/bin/env python3
# Unit tests for G-code driver handlers

import pytest
import asyncio
import time
import uuid
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from dataclasses import dataclass
from enum import Enum


# Mock classes for testing
class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    status: ExecutionStatus
    gcode: str = ""
    response: dict = None
    error_message: str = ""


@dataclass
class GCodeCommand:
    raw_command: str = ""


@dataclass
class TranslationResult:
    success: bool
    translated_commands: list
    error_message: str = ""


class MoonrakerClient:
    """Mock Moonraker client."""
    async def run_gcode(self, gcode):
        return ExecutionResult(status=ExecutionStatus.SUCCESS, gcode=gcode)


class CommandTranslator:
    """Mock command translator."""
    def translate_command(self, command, context=None):
        return TranslationResult(success=True, translated_commands=[command.raw_command])
    
    def parse_and_translate(self, gcode, context=None):
        return [TranslationResult(success=True, translated_commands=[gcode])]
    
    def get_moonraker_client(self):
        return MoonrakerClient()
    
    def reset_context(self):
        pass


# Import handlers module classes
from gcode_driver.handlers import (
    QueuedCommand,
    ExecutionHistoryEntry,
    ExecutionState,
    CommandQueue,
    ExecutionHistory,
    ExecutionHandler,
    GCodeExecutionManager,
    HandlerError,
    QueueError,
    ExecutionTimeoutError,
    CancellationError
)


@pytest.fixture
def mock_moonraker_client():
    """Create a mock Moonraker client."""
    return Mock(spec=MoonrakerClient)


@pytest.fixture
def mock_translator():
    """Create a mock command translator."""
    return Mock(spec=CommandTranslator)


@pytest.fixture
def execution_handler(mock_moonraker_client, mock_translator):
    """Create an ExecutionHandler instance for testing."""
    return ExecutionHandler(
        moonraker_client=mock_moonraker_client,
        translator=mock_translator,
        max_queue_size=100,
        max_history_entries=100,
        default_timeout=30.0
    )


class TestQueuedCommand:
    """Test QueuedCommand dataclass."""
    
    def test_queued_command_creation(self):
        """Test creating a queued command."""
        cmd = QueuedCommand(
            id="test_id",
            command="G0 X100",
            priority=1,
            context={'test': 'data'},
            metadata={'source': 'test'}
        )
        
        assert cmd.id == "test_id"
        assert cmd.command == "G0 X100"
        assert cmd.priority == 1
        assert cmd.context == {'test': 'data'}
        assert cmd.metadata == {'source': 'test'}
    
    def test_queued_command_auto_id(self):
        """Test queued command with auto-generated ID."""
        cmd = QueuedCommand(
            id="",
            command="G0 X100",
            priority=0
        )
        
        assert cmd.id != ""
        assert len(cmd.id) > 0


class TestExecutionHistoryEntry:
    """Test ExecutionHistoryEntry dataclass."""
    
    def test_history_entry_creation(self):
        """Test creating a history entry."""
        entry = ExecutionHistoryEntry(
            id="entry_id",
            gcode="G0 X100",
            status=ExecutionStatus.SUCCESS,
            timestamp=123456.789,
            execution_time=1.5,
            response={'queued': True},
            error_message=None,
            metadata={'test': 'data'}
        )
        
        assert entry.id == "entry_id"
        assert entry.gcode == "G0 X100"
        assert entry.status == ExecutionStatus.SUCCESS
        assert entry.timestamp == 123456.789
        assert entry.execution_time == 1.5
        assert entry.response == {'queued': True}
        assert entry.error_message is None
        assert entry.metadata == {'test': 'data'}
    
    def test_history_entry_to_dict(self):
        """Test converting history entry to dictionary."""
        entry = ExecutionHistoryEntry(
            id="entry_id",
            gcode="G0 X100",
            status=ExecutionStatus.SUCCESS,
            timestamp=123456.789,
            execution_time=1.5
        )
        
        result = entry.to_dict()
        
        assert result['id'] == "entry_id"
        assert result['gcode'] == "G0 X100"
        assert result['status'] == "success"
        assert 'datetime' in result
        assert result['execution_time'] == 1.5


class TestCommandQueue:
    """Test CommandQueue class."""
    
    @pytest.mark.asyncio
    async def test_enqueue_command(self, execution_handler):
        """Test enqueuing a command."""
        cmd_id = await execution_handler.queue.enqueue(
            "G0 X100",
            priority=1
        )
        
        assert cmd_id is not None
        assert len(cmd_id) > 0
    
    @pytest.mark.asyncio
    async def test_enqueue_with_priority(self, execution_handler):
        """Test enqueuing with priority ordering."""
        # Enqueue commands with different priorities
        id1 = await execution_handler.queue.enqueue("G0 X100", priority=1)
        id2 = await execution_handler.queue.enqueue("G0 X200", priority=3)
        id3 = await execution_handler.queue.enqueue("G0 X300", priority=2)
        
        # Verify queue size
        size = await execution_handler.queue.size()
        assert size == 3
    
    @pytest.mark.asyncio
    async def test_enqueue_queue_full(self, execution_handler):
        """Test enqueuing when queue is full."""
        # Create a queue with small max size
        small_queue = CommandQueue(max_size=2)
        
        # Fill queue
        await small_queue.enqueue("G0 X100")
        await small_queue.enqueue("G0 X200")
        
        # Try to add third command
        with pytest.raises(QueueError) as exc_info:
            await small_queue.enqueue("G0 X300")
        
        assert 'Queue is full' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_dequeue_command(self, execution_handler):
        """Test dequeuing a command."""
        # Enqueue a command first
        await execution_handler.queue.enqueue("G0 X100")
        
        # Dequeue
        cmd = await execution_handler.queue.dequeue()
        
        assert cmd is not None
        assert cmd.command == "G0 X100"
    
    @pytest.mark.asyncio
    async def test_dequeue_empty_queue(self, execution_handler):
        """Test dequeuing from empty queue."""
        cmd = await execution_handler.queue.dequeue()
        
        assert cmd is None
    
    @pytest.mark.asyncio
    async def test_peek_command(self, execution_handler):
        """Test peeking at next command."""
        # Enqueue a command
        await execution_handler.queue.enqueue("G0 X100")
        
        # Peek
        cmd = await execution_handler.queue.peek()
        
        assert cmd is not None
        assert cmd.command == "G0 X100"
        
        # Verify command is still in queue
        size = await execution_handler.queue.size()
        assert size == 1
    
    @pytest.mark.asyncio
    async def test_peek_empty_queue(self, execution_handler):
        """Test peeking at empty queue."""
        cmd = await execution_handler.queue.peek()
        
        assert cmd is None
    
    @pytest.mark.asyncio
    async def test_queue_size(self, execution_handler):
        """Test getting queue size."""
        size = await execution_handler.queue.size()
        
        assert size == 0
        
        # Add commands
        await execution_handler.queue.enqueue("G0 X100")
        await execution_handler.queue.enqueue("G0 X200")
        
        size = await execution_handler.queue.size()
        assert size == 2
    
    @pytest.mark.asyncio
    async def test_clear_queue(self, execution_handler):
        """Test clearing the queue."""
        # Add commands
        await execution_handler.queue.enqueue("G0 X100")
        await execution_handler.queue.enqueue("G0 X200")
        
        # Clear
        await execution_handler.queue.clear()
        
        # Verify empty
        size = await execution_handler.queue.size()
        assert size == 0
    
    @pytest.mark.asyncio
    async def test_remove_command(self, execution_handler):
        """Test removing a specific command."""
        # Add commands
        id1 = await execution_handler.queue.enqueue("G0 X100")
        id2 = await execution_handler.queue.enqueue("G0 X200")
        
        # Remove first command
        removed = await execution_handler.queue.remove(id1)
        
        assert removed == True
        
        # Verify only one command remains
        size = await execution_handler.queue.size()
        assert size == 1
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_command(self, execution_handler):
        """Test removing non-existent command."""
        removed = await execution_handler.queue.remove("nonexistent_id")
        
        assert removed == False
    
    @pytest.mark.asyncio
    async def test_get_queue_snapshot(self, execution_handler):
        """Test getting queue snapshot."""
        # Add commands
        await execution_handler.queue.enqueue("G0 X100 Y50 Z10", metadata={'test': 'data1'})
        await execution_handler.queue.enqueue("G0 X200 Y100 Z20", metadata={'test': 'data2'})
        
        # Get snapshot
        snapshot = await execution_handler.queue.get_queue_snapshot()
        
        assert len(snapshot) == 2
        assert 'command' in snapshot[0]
        assert 'priority' in snapshot[0]
        assert 'metadata' in snapshot[0]


class TestExecutionHistory:
    """Test ExecutionHistory class."""
    
    @pytest.mark.asyncio
    async def test_add_entry(self, execution_handler):
        """Test adding a history entry."""
        entry = ExecutionHistoryEntry(
            id="entry_id",
            gcode="G0 X100",
            status=ExecutionStatus.SUCCESS,
            timestamp=123456.789,
            execution_time=1.5
        )
        
        await execution_handler.history.add_entry(entry)
        
        # Verify entry was added
        history = await execution_handler.history.get_history()
        assert len(history) == 1
        assert history[0].id == "entry_id"
    
    @pytest.mark.asyncio
    async def test_get_history(self, execution_handler):
        """Test getting history."""
        # Add entries
        entry1 = ExecutionHistoryEntry(
            id="entry1",
            gcode="G0 X100",
            status=ExecutionStatus.SUCCESS,
            timestamp=123456.789,
            execution_time=1.5
        )
        entry2 = ExecutionHistoryEntry(
            id="entry2",
            gcode="G0 X200",
            status=ExecutionStatus.FAILED,
            timestamp=123457.789,
            execution_time=0.5,
            error_message="Failed"
        )
        
        await execution_handler.history.add_entry(entry1)
        await execution_handler.history.add_entry(entry2)
        
        # Get all history
        history = await execution_handler.history.get_history()
        assert len(history) == 2
    
    @pytest.mark.asyncio
    async def test_get_history_with_limit(self, execution_handler):
        """Test getting history with limit."""
        # Add 3 entries
        for i in range(3):
            entry = ExecutionHistoryEntry(
                id=f"entry{i}",
                gcode=f"G0 X{i*100}",
                status=ExecutionStatus.SUCCESS,
                timestamp=123456.789 + i,
                execution_time=1.0
            )
            await execution_handler.history.add_entry(entry)
        
        # Get with limit
        history = await execution_handler.history.get_history(limit=2)
        assert len(history) == 2
    
    @pytest.mark.asyncio
    async def test_get_history_with_status_filter(self, execution_handler):
        """Test getting history filtered by status."""
        # Add entries with different statuses
        entry1 = ExecutionHistoryEntry(
            id="entry1",
            gcode="G0 X100",
            status=ExecutionStatus.SUCCESS,
            timestamp=123456.789,
            execution_time=1.5
        )
        entry2 = ExecutionHistoryEntry(
            id="entry2",
            gcode="G0 X200",
            status=ExecutionStatus.FAILED,
            timestamp=123457.789,
            execution_time=0.5
        )
        
        await execution_handler.history.add_entry(entry1)
        await execution_handler.history.add_entry(entry2)
        
        # Get successful entries only
        history = await execution_handler.history.get_history(status=ExecutionStatus.SUCCESS)
        assert len(history) == 1
        assert history[0].id == "entry1"
    
    @pytest.mark.asyncio
    async def test_get_entry(self, execution_handler):
        """Test getting specific history entry."""
        entry = ExecutionHistoryEntry(
            id="entry_id",
            gcode="G0 X100",
            status=ExecutionStatus.SUCCESS,
            timestamp=123456.789,
            execution_time=1.5
        )
        
        await execution_handler.history.add_entry(entry)
        
        # Get entry
        retrieved = await execution_handler.history.get_entry("entry_id")
        assert retrieved is not None
        assert retrieved.id == "entry_id"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_entry(self, execution_handler):
        """Test getting non-existent history entry."""
        retrieved = await execution_handler.history.get_entry("nonexistent_id")
        
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_clear_history(self, execution_handler):
        """Test clearing history."""
        # Add entry
        entry = ExecutionHistoryEntry(
            id="entry_id",
            gcode="G0 X100",
            status=ExecutionStatus.SUCCESS,
            timestamp=123456.789,
            execution_time=1.5
        )
        await execution_handler.history.add_entry(entry)
        
        # Clear
        await execution_handler.history.clear()
        
        # Verify empty
        history = await execution_handler.history.get_history()
        assert len(history) == 0
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, execution_handler):
        """Test getting history statistics."""
        # Add entries
        for i in range(5):
            entry = ExecutionHistoryEntry(
                id=f"entry{i}",
                gcode=f"G0 X{i*100}",
                status=ExecutionStatus.SUCCESS if i < 4 else ExecutionStatus.FAILED,
                timestamp=123456.789 + i,
                execution_time=1.0 + i * 0.1
            )
            await execution_handler.history.add_entry(entry)
        
        # Get statistics
        stats = await execution_handler.history.get_statistics()
        
        assert stats['total'] == 5
        assert stats['completed'] == 4
        assert stats['failed'] == 1
        assert stats['success_rate'] == pytest.approx(80.0, abs=0.1)


class TestExecutionHandler:
    """Test ExecutionHandler class."""
    
    @pytest.mark.asyncio
    async def test_execute_single_success(self, execution_handler, mock_moonraker_client):
        """Test successful single command execution."""
        mock_moonraker_client.run_gcode = AsyncMock(
            return_value=ExecutionResult(status=ExecutionStatus.SUCCESS, gcode="G0 X100")
        )
        
        result = await execution_handler.execute_single("G0 X100")
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.gcode == "G0 X100"
    
    @pytest.mark.asyncio
    async def test_execute_single_timeout(self, execution_handler, mock_moonraker_client):
        """Test single command execution with timeout."""
        async def slow_gcode(gcode):
            await asyncio.sleep(2.0)
            return ExecutionResult(status=ExecutionStatus.SUCCESS, gcode=gcode)
        
        mock_moonraker_client.run_gcode = AsyncMock(side_effect=slow_gcode)
        
        # Execute with short timeout
        with pytest.raises(ExecutionTimeoutError) as exc_info:
            await execution_handler.execute_single("G0 X100", timeout=0.1)
        
        assert 'timed out' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_execute_single_with_metadata(self, execution_handler, mock_moonraker_client):
        """Test single command execution with metadata."""
        mock_moonraker_client.run_gcode = AsyncMock(
            return_value=ExecutionResult(status=ExecutionStatus.SUCCESS, gcode="G0 X100")
        )
        
        result = await execution_handler.execute_single(
            "G0 X100",
            metadata={'test': 'data'}
        )
        
        assert result.status == ExecutionStatus.SUCCESS
        
        # Verify history entry has metadata
        history = await execution_handler.history.get_history()
        assert len(history) == 1
        assert history[0].metadata == {'test': 'data'}
    
    @pytest.mark.asyncio
    async def test_execute_batch_success(self, execution_handler, mock_moonraker_client):
        """Test successful batch execution."""
        gcodes = ["G0 X100", "G0 Y100", "G0 Z100"]
        mock_moonraker_client.run_gcode = AsyncMock(
            return_value=ExecutionResult(status=ExecutionStatus.SUCCESS, gcode="test")
        )
        
        results = await execution_handler.execute_batch(gcodes)
        
        assert len(results) == 3
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)
    
    @pytest.mark.asyncio
    async def test_execute_batch_stop_on_error(self, execution_handler, mock_moonraker_client):
        """Test batch execution stopping on error."""
        gcodes = ["G0 X100", "G0 Y100", "G0 Z100"]
        
        call_count = [0]
        
        async def failing_gcode(gcode):
            call_count[0] += 1
            if call_count[0] == 2:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    gcode=gcode,
                    error_message="Failed"
                )
            return ExecutionResult(status=ExecutionStatus.SUCCESS, gcode=gcode)
        
        mock_moonraker_client.run_gcode = AsyncMock(side_effect=failing_gcode)
        
        results = await execution_handler.execute_batch(gcodes, stop_on_error=True)
        
        # Should stop after error
        assert len(results) == 2
        assert results[1].status == ExecutionStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_enqueue_command(self, execution_handler):
        """Test enqueuing a command."""
        cmd_id = await execution_handler.enqueue_command(
            "G0 X100",
            priority=1
        )
        
        assert cmd_id is not None
        assert len(cmd_id) > 0
    
    @pytest.mark.asyncio
    async def test_process_queue(self, execution_handler, mock_moonraker_client):
        """Test processing queue."""
        # Enqueue commands
        await execution_handler.enqueue_command("G0 X100")
        await execution_handler.enqueue_command("G0 Y100")
        
        mock_moonraker_client.run_gcode = AsyncMock(
            return_value=ExecutionResult(status=ExecutionStatus.SUCCESS, gcode="test")
        )
        
        # Process queue
        results = await execution_handler.process_queue()
        
        assert len(results) == 2
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)
    
    @pytest.mark.asyncio
    async def test_cancel_execution(self, execution_handler):
        """Test cancelling execution."""
        # Set cancellation token
        execution_handler._cancellation_token = asyncio.Event()
        
        await execution_handler.cancel_execution()
        
        # Verify state changed
        state = await execution_handler.get_state()
        assert state == ExecutionState.STOPPED
    
    @pytest.mark.asyncio
    async def test_pause_and_resume(self, execution_handler):
        """Test pause and resume."""
        # Pause
        await execution_handler.pause()
        state = await execution_handler.get_state()
        assert state == ExecutionState.PAUSED
        
        # Resume
        await execution_handler.resume()
        state = await execution_handler.get_state()
        assert state == ExecutionState.IDLE
    
    @pytest.mark.asyncio
    async def test_get_queue_status(self, execution_handler):
        """Test getting queue status."""
        # Enqueue commands
        await execution_handler.enqueue_command("G0 X100")
        await execution_handler.enqueue_command("G0 Y100")
        
        status = await execution_handler.get_queue_status()
        
        assert status['size'] == 2
        assert 'snapshot' in status
        assert len(status['snapshot']) == 2
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, execution_handler, mock_moonraker_client):
        """Test getting execution statistics."""
        # Execute some commands
        mock_moonraker_client.run_gcode = AsyncMock(
            return_value=ExecutionResult(status=ExecutionStatus.SUCCESS, gcode="test")
        )
        
        await execution_handler.execute_single("G0 X100")
        await execution_handler.execute_single("G0 Y100")
        
        stats = await execution_handler.get_statistics()
        
        assert 'state' in stats
        assert 'queue_size' in stats
        assert 'history' in stats
    
    @pytest.mark.asyncio
    async def test_clear_queue(self, execution_handler):
        """Test clearing queue."""
        # Enqueue commands
        await execution_handler.enqueue_command("G0 X100")
        await execution_handler.enqueue_command("G0 Y100")
        
        # Clear
        await execution_handler.clear_queue()
        
        # Verify empty
        status = await execution_handler.get_queue_status()
        assert status['size'] == 0
    
    @pytest.mark.asyncio
    async def test_clear_history(self, execution_handler):
        """Test clearing history."""
        # Execute commands to create history
        mock_moonraker_client = execution_handler.moonraker_client
        mock_moonraker_client.run_gcode = AsyncMock(
            return_value=ExecutionResult(status=ExecutionStatus.SUCCESS, gcode="test")
        )
        
        await execution_handler.execute_single("G0 X100")
        
        # Clear
        await execution_handler.clear_history()
        
        # Verify empty
        history = await execution_handler.history.get_history()
        assert len(history) == 0
    
    @pytest.mark.asyncio
    async def test_reset(self, execution_handler):
        """Test resetting handler."""
        # Enqueue commands and execute
        mock_moonraker_client = execution_handler.moonraker_client
        mock_moonraker_client.run_gcode = AsyncMock(
            return_value=ExecutionResult(status=ExecutionStatus.SUCCESS, gcode="test")
        )
        
        await execution_handler.enqueue_command("G0 X100")
        await execution_handler.process_queue()
        
        # Reset
        await execution_handler.reset()
        
        # Verify reset
        status = await execution_handler.get_queue_status()
        assert status['size'] == 0
        
        history = await execution_handler.history.get_history()
        assert len(history) == 0


class TestGCodeExecutionManager:
    """Test GCodeExecutionManager class."""
    
    @pytest.mark.asyncio
    async def test_execute_single_gcode(self, execution_handler, mock_moonraker_client):
        """Test executing single G-code."""
        mock_moonraker_client.run_gcode = AsyncMock(
            return_value=ExecutionResult(status=ExecutionStatus.SUCCESS, gcode="G0 X100")
        )
        
        manager = GCodeExecutionManager(
            moonraker_host='localhost',
            moonraker_port=7125
        )
        manager._handler = execution_handler
        
        result = await manager.execute("G0 X100")
        
        assert result.status == ExecutionStatus.SUCCESS
    
    @pytest.mark.asyncio
    async def test_execute_batch_gcode(self, execution_handler, mock_moonraker_client):
        """Test executing batch G-code."""
        gcodes = ["G0 X100", "G0 Y100"]
        mock_moonraker_client.run_gcode = AsyncMock(
            return_value=ExecutionResult(status=ExecutionStatus.SUCCESS, gcode="test")
        )
        
        manager = GCodeExecutionManager(
            moonraker_host='localhost',
            moonraker_port=7125
        )
        manager._handler = execution_handler
        
        results = await manager.execute(gcodes)
        
        assert len(results) == 2
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)
    
    @pytest.mark.asyncio
    async def test_parse_and_execute(self, execution_handler, mock_translator):
        """Test parsing and executing G-code."""
        mock_translator.parse_and_translate = Mock(
            return_value=[
                TranslationResult(success=True, translated_commands=["G0 X100"])
            ]
        )
        
        manager = GCodeExecutionManager(
            moonraker_host='localhost',
            moonraker_port=7125
        )
        manager._handler = execution_handler
        manager.translator = mock_translator
        
        results = await manager.parse_and_execute("G0 X100")
        
        assert len(results) == 1
        assert results[0].status == ExecutionStatus.SUCCESS
    
    @pytest.mark.asyncio
    async def test_cancel(self, execution_handler):
        """Test cancelling execution."""
        manager = GCodeExecutionManager(
            moonraker_host='localhost',
            moonraker_port=7125
        )
        manager._handler = execution_handler
        
        await manager.cancel()
        
        # Verify cancellation
        state = await execution_handler.get_state()
        assert state == ExecutionState.STOPPED
    
    @pytest.mark.asyncio
    async def test_pause_and_resume(self, execution_handler):
        """Test pause and resume."""
        manager = GCodeExecutionManager(
            moonraker_host='localhost',
            moonraker_port=7125
        )
        manager._handler = execution_handler
        
        await manager.pause()
        state = await execution_handler.get_state()
        assert state == ExecutionState.PAUSED
        
        await manager.resume()
        state = await execution_handler.get_state()
        assert state == ExecutionState.IDLE
    
    @pytest.mark.asyncio
    async def test_reset(self, execution_handler, mock_translator):
        """Test resetting manager."""
        manager = GCodeExecutionManager(
            moonraker_host='localhost',
            moonraker_port=7125
        )
        manager._handler = execution_handler
        manager.translator = mock_translator
        
        # Enqueue and execute
        await execution_handler.enqueue_command("G0 X100")
        await execution_handler.process_queue()
        
        # Reset
        await manager.reset()
        
        # Verify reset
        status = await execution_handler.get_queue_status()
        assert status['size'] == 0
        
        history = await execution_handler.history.get_history()
        assert len(history) == 0


class TestExceptions:
    """Test exception classes."""
    
    def test_handler_error(self):
        """Test HandlerError exception."""
        with pytest.raises(HandlerError) as exc_info:
            raise HandlerError("Test error")
        
        assert str(exc_info.value) == "Test error"
    
    def test_queue_error(self):
        """Test QueueError exception."""
        with pytest.raises(QueueError) as exc_info:
            raise QueueError("Queue error")
        
        assert str(exc_info.value) == "Queue error"
        assert isinstance(exc_info.value, HandlerError)
    
    def test_execution_timeout_error(self):
        """Test ExecutionTimeoutError exception."""
        with pytest.raises(ExecutionTimeoutError) as exc_info:
            raise ExecutionTimeoutError("Timeout error")
        
        assert str(exc_info.value) == "Timeout error"
        assert isinstance(exc_info.value, HandlerError)
    
    def test_cancellation_error(self):
        """Test CancellationError exception."""
        with pytest.raises(CancellationError) as exc_info:
            raise CancellationError("Cancelled")
        
        assert str(exc_info.value) == "Cancelled"
        assert isinstance(exc_info.value, HandlerError)
