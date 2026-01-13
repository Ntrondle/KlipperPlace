#!/usr/bin/env python3
# Execution Handlers for KlipperPlace
# Provides command execution, queuing, batch processing, and management

import logging
import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from datetime import datetime
import json

# Import from translator module
from .translator import (
    MoonrakerClient,
    CommandTranslator,
    ExecutionResult,
    ExecutionStatus,
    TranslationContext
)

# Import from parser module
from .parser import (
    GCodeCommand,
    GCodeCommandType,
    TranslationResult
)

# Component logging
logger = logging.getLogger(__name__)


class HandlerError(Exception):
    """Base exception for handler errors."""
    pass


class QueueError(HandlerError):
    """Exception raised for queue-related errors."""
    pass


class ExecutionTimeoutError(HandlerError):
    """Exception raised when execution times out."""
    pass


class CancellationError(HandlerError):
    """Exception raised when execution is cancelled."""
    pass


@dataclass
class QueuedCommand:
    """Represents a command in the execution queue."""
    id: str
    command: Union[str, GCodeCommand]
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class ExecutionHistoryEntry:
    """Represents an entry in the execution history."""
    id: str
    gcode: str
    status: ExecutionStatus
    timestamp: float
    execution_time: float
    response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary."""
        return {
            'id': self.id,
            'gcode': self.gcode,
            'status': self.status.value,
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat(),
            'execution_time': self.execution_time,
            'response': self.response,
            'error_message': self.error_message,
            'metadata': self.metadata
        }


class ExecutionState(Enum):
    """State of the execution handler."""
    IDLE = "idle"
    EXECUTING = "executing"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class CommandQueue:
    """Manages command queuing with priority support."""
    
    def __init__(self, max_size: int = 1000):
        """Initialize command queue.
        
        Args:
            max_size: Maximum number of commands in queue
        """
        self.max_size = max_size
        self._queue: deque[QueuedCommand] = deque()
        self._lock = asyncio.Lock()
        
        logger.info(f"Command queue initialized with max size: {max_size}")
    
    async def enqueue(self, command: Union[str, GCodeCommand], 
                     priority: int = 0,
                     context: Optional[Dict[str, Any]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a command to the queue.
        
        Args:
            command: Command to enqueue
            priority: Command priority (higher = executed first)
            context: Optional execution context
            metadata: Optional metadata
            
        Returns:
            Command ID
            
        Raises:
            QueueError: If queue is full
        """
        async with self._lock:
            if len(self._queue) >= self.max_size:
                raise QueueError(f"Queue is full (max size: {self.max_size})")
            
            queued_cmd = QueuedCommand(
                id=str(uuid.uuid4()),
                command=command,
                priority=priority,
                context=context,
                metadata=metadata or {}
            )
            
            # Insert in priority order (higher priority first)
            inserted = False
            for i, cmd in enumerate(self._queue):
                if priority > cmd.priority:
                    self._queue.insert(i, queued_cmd)
                    inserted = True
                    break
            
            if not inserted:
                self._queue.append(queued_cmd)
            
            logger.debug(f"Enqueued command {queued_cmd.id} with priority {priority}")
            return queued_cmd.id
    
    async def dequeue(self) -> Optional[QueuedCommand]:
        """Remove and return the next command from the queue.
        
        Returns:
            QueuedCommand or None if queue is empty
        """
        async with self._lock:
            if not self._queue:
                return None
            
            cmd = self._queue.popleft()
            logger.debug(f"Dequeued command {cmd.id}")
            return cmd
    
    async def peek(self) -> Optional[QueuedCommand]:
        """Peek at the next command without removing it.
        
        Returns:
            QueuedCommand or None if queue is empty
        """
        async with self._lock:
            return self._queue[0] if self._queue else None
    
    async def size(self) -> int:
        """Get current queue size.
        
        Returns:
            Number of commands in queue
        """
        async with self._lock:
            return len(self._queue)
    
    async def clear(self) -> None:
        """Clear all commands from the queue."""
        async with self._lock:
            count = len(self._queue)
            self._queue.clear()
            logger.info(f"Cleared {count} commands from queue")
    
    async def remove(self, command_id: str) -> bool:
        """Remove a specific command from the queue.
        
        Args:
            command_id: ID of command to remove
            
        Returns:
            True if command was removed, False if not found
        """
        async with self._lock:
            for i, cmd in enumerate(self._queue):
                if cmd.id == command_id:
                    self._queue.remove(cmd)
                    logger.debug(f"Removed command {command_id} from queue")
                    return True
            return False
    
    async def get_queue_snapshot(self) -> List[Dict[str, Any]]:
        """Get a snapshot of the current queue.
        
        Returns:
            List of command dictionaries
        """
        async with self._lock:
            return [
                {
                    'id': cmd.id,
                    'command': str(cmd.command)[:100],
                    'priority': cmd.priority,
                    'created_at': cmd.created_at,
                    'metadata': cmd.metadata
                }
                for cmd in self._queue
            ]


class ExecutionHistory:
    """Manages execution history with configurable retention."""
    
    def __init__(self, max_entries: int = 1000):
        """Initialize execution history.
        
        Args:
            max_entries: Maximum number of history entries to retain
        """
        self.max_entries = max_entries
        self._history: List[ExecutionHistoryEntry] = []
        self._lock = asyncio.Lock()
        
        logger.info(f"Execution history initialized with max entries: {max_entries}")
    
    async def add_entry(self, entry: ExecutionHistoryEntry) -> None:
        """Add an entry to the history.
        
        Args:
            entry: History entry to add
        """
        async with self._lock:
            self._history.append(entry)
            
            # Trim if over max size
            if len(self._history) > self.max_entries:
                removed = len(self._history) - self.max_entries
                self._history = self._history[-self.max_entries:]
                logger.debug(f"Trimmed {removed} old entries from history")
    
    async def get_history(self, limit: Optional[int] = None,
                         status: Optional[ExecutionStatus] = None,
                         since: Optional[float] = None) -> List[ExecutionHistoryEntry]:
        """Get execution history entries.
        
        Args:
            limit: Maximum number of entries to return
            status: Filter by execution status
            since: Only return entries after this timestamp
            
        Returns:
            List of history entries
        """
        async with self._lock:
            entries = self._history.copy()
            
            # Filter by status
            if status:
                entries = [e for e in entries if e.status == status]
            
            # Filter by timestamp
            if since:
                entries = [e for e in entries if e.timestamp >= since]
            
            # Apply limit
            if limit:
                entries = entries[-limit:]
            
            return entries
    
    async def get_entry(self, entry_id: str) -> Optional[ExecutionHistoryEntry]:
        """Get a specific history entry by ID.
        
        Args:
            entry_id: ID of entry to retrieve
            
        Returns:
            History entry or None if not found
        """
        async with self._lock:
            for entry in self._history:
                if entry.id == entry_id:
                    return entry
            return None
    
    async def clear(self) -> None:
        """Clear all history entries."""
        async with self._lock:
            count = len(self._history)
            self._history.clear()
            logger.info(f"Cleared {count} entries from history")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics.
        
        Returns:
            Dictionary containing statistics
        """
        async with self._lock:
            if not self._history:
                return {
                    'total': 0,
                    'completed': 0,
                    'failed': 0,
                    'cancelled': 0,
                    'success_rate': 0.0,
                    'avg_execution_time': 0.0
                }
            
            total = len(self._history)
            completed = sum(1 for e in self._history if e.status == ExecutionStatus.COMPLETED)
            failed = sum(1 for e in self._history if e.status == ExecutionStatus.FAILED)
            cancelled = sum(1 for e in self._history if e.status == ExecutionStatus.CANCELLED)
            
            success_rate = (completed / total * 100) if total > 0 else 0.0
            
            avg_time = 0.0
            if completed > 0:
                completed_times = [e.execution_time for e in self._history 
                                  if e.status == ExecutionStatus.COMPLETED]
                avg_time = sum(completed_times) / len(completed_times)
            
            return {
                'total': total,
                'completed': completed,
                'failed': failed,
                'cancelled': cancelled,
                'success_rate': success_rate,
                'avg_execution_time': avg_time
            }


class ExecutionHandler:
    """Main execution handler for G-code commands."""
    
    def __init__(self, moonraker_client: MoonrakerClient,
                 translator: Optional[CommandTranslator] = None,
                 max_queue_size: int = 1000,
                 max_history_entries: int = 1000,
                 default_timeout: float = 30.0):
        """Initialize execution handler.
        
        Args:
            moonraker_client: Moonraker client for API communication
            translator: Optional command translator
            max_queue_size: Maximum queue size
            max_history_entries: Maximum history entries
            default_timeout: Default execution timeout in seconds
        """
        self.moonraker_client = moonraker_client
        self.translator = translator
        self.default_timeout = default_timeout
        
        # Queue and history
        self.queue = CommandQueue(max_queue_size)
        self.history = ExecutionHistory(max_history_entries)
        
        # State management
        self._state = ExecutionState.IDLE
        self._state_lock = asyncio.Lock()
        self._cancellation_token: Optional[asyncio.Event] = None
        
        # Event callbacks
        self._on_command_start: Optional[Callable[[str], None]] = None
        self._on_command_complete: Optional[Callable[[str, ExecutionResult], None]] = None
        self._on_command_error: Optional[Callable[[str, Exception], None]] = None
        self._on_state_change: Optional[Callable[[ExecutionState, ExecutionState], None]] = None
        
        logger.info("Execution handler initialized")
    
    async def get_state(self) -> ExecutionState:
        """Get current handler state.
        
        Returns:
            Current execution state
        """
        async with self._state_lock:
            return self._state
    
    async def _set_state(self, new_state: ExecutionState) -> None:
        """Set handler state and trigger callback.
        
        Args:
            new_state: New state to set
        """
        async with self._state_lock:
            old_state = self._state
            self._state = new_state
            
            if old_state != new_state and self._on_state_change:
                try:
                    self._on_state_change(old_state, new_state)
                except Exception as e:
                    logger.error(f"Error in state change callback: {e}")
            
            logger.debug(f"State changed: {old_state.value} -> {new_state.value}")
    
    def set_callbacks(self,
                     on_command_start: Optional[Callable[[str], None]] = None,
                     on_command_complete: Optional[Callable[[str, ExecutionResult], None]] = None,
                     on_command_error: Optional[Callable[[str, Exception], None]] = None,
                     on_state_change: Optional[Callable[[ExecutionState, ExecutionState], None]] = None) -> None:
        """Set event callbacks.
        
        Args:
            on_command_start: Called when command starts execution
            on_command_complete: Called when command completes
            on_command_error: Called when command errors
            on_state_change: Called when handler state changes
        """
        self._on_command_start = on_command_start
        self._on_command_complete = on_command_complete
        self._on_command_error = on_command_error
        self._on_state_change = on_state_change
    
    async def execute_single(self, gcode: str,
                            timeout: Optional[float] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute a single G-code command.
        
        Args:
            gcode: G-code string to execute
            timeout: Execution timeout in seconds (uses default if None)
            metadata: Optional metadata for history
            
        Returns:
            ExecutionResult object
        """
        timeout = timeout or self.default_timeout
        command_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(f"Executing command {command_id}: {gcode[:100]}")
        
        # Trigger start callback
        if self._on_command_start:
            try:
                self._on_command_start(command_id)
            except Exception as e:
                logger.error(f"Error in command start callback: {e}")
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self.moonraker_client.run_gcode(gcode),
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # Create history entry
            entry = ExecutionHistoryEntry(
                id=command_id,
                gcode=gcode,
                status=result.status,
                timestamp=start_time,
                execution_time=execution_time,
                response=result.response,
                error_message=result.error_message,
                metadata=metadata or {}
            )
            await self.history.add_entry(entry)
            
            # Trigger complete callback
            if self._on_command_complete:
                try:
                    self._on_command_complete(command_id, result)
                except Exception as e:
                    logger.error(f"Error in command complete callback: {e}")
            
            logger.info(f"Command {command_id} completed in {execution_time:.3f}s")
            return result
        
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            error = ExecutionTimeoutError(f"Command execution timed out after {timeout}s")
            
            # Create failed history entry
            entry = ExecutionHistoryEntry(
                id=command_id,
                gcode=gcode,
                status=ExecutionStatus.FAILED,
                timestamp=start_time,
                execution_time=execution_time,
                error_message=str(error),
                metadata=metadata or {}
            )
            await self.history.add_entry(entry)
            
            # Trigger error callback
            if self._on_command_error:
                try:
                    self._on_command_error(command_id, error)
                except Exception as e:
                    logger.error(f"Error in command error callback: {e}")
            
            logger.error(f"Command {command_id} timed out")
            raise error
        
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Create failed history entry
            entry = ExecutionHistoryEntry(
                id=command_id,
                gcode=gcode,
                status=ExecutionStatus.FAILED,
                timestamp=start_time,
                execution_time=execution_time,
                error_message=str(e),
                metadata=metadata or {}
            )
            await self.history.add_entry(entry)
            
            # Trigger error callback
            if self._on_command_error:
                try:
                    self._on_command_error(command_id, e)
                except Exception as err:
                    logger.error(f"Error in command error callback: {err}")
            
            logger.error(f"Command {command_id} failed: {e}")
            raise
    
    async def execute_batch(self, gcodes: List[str],
                           stop_on_error: bool = True,
                           timeout: Optional[float] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> List[ExecutionResult]:
        """Execute multiple G-code commands as a batch.
        
        Args:
            gcodes: List of G-code strings to execute
            stop_on_error: Stop execution on first error
            timeout: Timeout per command (uses default if None)
            metadata: Optional metadata for history
            
        Returns:
            List of ExecutionResult objects
        """
        results = []
        batch_id = str(uuid.uuid4())
        
        logger.info(f"Starting batch execution {batch_id} with {len(gcodes)} commands")
        
        await self._set_state(ExecutionState.EXECUTING)
        
        try:
            for i, gcode in enumerate(gcodes):
                # Check for cancellation
                if self._cancellation_token and self._cancellation_token.is_set():
                    logger.warning(f"Batch {batch_id} cancelled at command {i+1}/{len(gcodes)}")
                    raise CancellationError("Batch execution cancelled")
                
                try:
                    result = await self.execute_single(
                        gcode,
                        timeout=timeout,
                        metadata={**(metadata or {}), 'batch_id': batch_id, 'batch_index': i}
                    )
                    results.append(result)
                    
                    if result.status == ExecutionStatus.FAILED and stop_on_error:
                        logger.error(f"Batch {batch_id} stopped due to error at command {i+1}")
                        break
                
                except Exception as e:
                    if stop_on_error:
                        logger.error(f"Batch {batch_id} stopped due to exception at command {i+1}: {e}")
                        raise
                    else:
                        # Add failed result and continue
                        results.append(ExecutionResult(
                            status=ExecutionStatus.FAILED,
                            gcode=gcode,
                            error_message=str(e)
                        ))
            
            logger.info(f"Batch {batch_id} completed: {len(results)} commands executed")
            return results
        
        finally:
            await self._set_state(ExecutionState.IDLE)
    
    async def enqueue_command(self, command: Union[str, GCodeCommand],
                             priority: int = 0,
                             context: Optional[Dict[str, Any]] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> str:
        """Enqueue a command for execution.
        
        Args:
            command: Command to enqueue
            priority: Command priority
            context: Optional execution context
            metadata: Optional metadata
            
        Returns:
            Command ID
        """
        command_id = await self.queue.enqueue(
            command,
            priority=priority,
            context=context,
            metadata=metadata
        )
        
        logger.info(f"Enqueued command {command_id} with priority {priority}")
        return command_id
    
    async def process_queue(self, stop_on_error: bool = True,
                           timeout: Optional[float] = None) -> List[ExecutionResult]:
        """Process all commands in the queue.
        
        Args:
            stop_on_error: Stop processing on first error
            timeout: Timeout per command
            
        Returns:
            List of ExecutionResult objects
        """
        results = []
        
        logger.info("Starting queue processing")
        await self._set_state(ExecutionState.EXECUTING)
        
        try:
            while True:
                # Check for cancellation
                if self._cancellation_token and self._cancellation_token.is_set():
                    logger.warning("Queue processing cancelled")
                    raise CancellationError("Queue processing cancelled")
                
                # Get next command
                queued_cmd = await self.queue.dequeue()
                if not queued_cmd:
                    break
                
                # Prepare G-code
                if isinstance(queued_cmd.command, GCodeCommand):
                    if self.translator:
                        # Translate command
                        translation_result = self.translator.translate_command(
                            queued_cmd.command,
                            queued_cmd.context
                        )
                        if not translation_result.success:
                            logger.error(f"Translation failed for command {queued_cmd.id}")
                            if stop_on_error:
                                raise HandlerError(f"Translation failed: {translation_result.error_message}")
                            continue
                        
                        gcodes = translation_result.translated_commands
                    else:
                        gcodes = [queued_cmd.command.raw_command]
                else:
                    gcodes = [queued_cmd.command]
                
                # Execute all translated G-codes
                for gcode in gcodes:
                    try:
                        result = await self.execute_single(
                            gcode,
                            timeout=timeout,
                            metadata={**(queued_cmd.metadata or {}), 'queued_command_id': queued_cmd.id}
                        )
                        results.append(result)
                        
                        if result.status == ExecutionStatus.FAILED and stop_on_error:
                            logger.error(f"Queue processing stopped due to error")
                            raise HandlerError(f"Command execution failed: {result.error_message}")
                    
                    except Exception as e:
                        if stop_on_error:
                            raise
                        else:
                            results.append(ExecutionResult(
                                status=ExecutionStatus.FAILED,
                                gcode=gcode,
                                error_message=str(e)
                            ))
            
            logger.info(f"Queue processing completed: {len(results)} commands executed")
            return results
        
        finally:
            await self._set_state(ExecutionState.IDLE)
    
    async def cancel_execution(self) -> None:
        """Cancel current execution."""
        logger.warning("Cancelling execution")
        
        if self._cancellation_token:
            self._cancellation_token.set()
        
        await self._set_state(ExecutionState.STOPPED)
    
    async def pause(self) -> None:
        """Pause execution (sets state to PAUSED)."""
        logger.info("Pausing execution")
        await self._set_state(ExecutionState.PAUSED)
    
    async def resume(self) -> None:
        """Resume execution from paused state."""
        logger.info("Resuming execution")
        await self._set_state(ExecutionState.IDLE)
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status.
        
        Returns:
            Dictionary containing queue status
        """
        return {
            'size': await self.queue.size(),
            'snapshot': await self.queue.get_queue_snapshot()
        }
    
    async def get_history(self, limit: Optional[int] = None,
                         status: Optional[ExecutionStatus] = None,
                         since: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get execution history.
        
        Args:
            limit: Maximum number of entries
            status: Filter by status
            since: Filter by timestamp
            
        Returns:
            List of history entry dictionaries
        """
        entries = await self.history.get_history(limit, status, since)
        return [entry.to_dict() for entry in entries]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics.
        
        Returns:
            Dictionary containing statistics
        """
        stats = await self.history.get_statistics()
        
        return {
            'state': (await self.get_state()).value,
            'queue_size': await self.queue.size(),
            'history': stats
        }
    
    async def clear_queue(self) -> None:
        """Clear the command queue."""
        await self.queue.clear()
        logger.info("Queue cleared")
    
    async def clear_history(self) -> None:
        """Clear execution history."""
        await self.history.clear()
        logger.info("History cleared")
    
    async def reset(self) -> None:
        """Reset handler to initial state."""
        await self.clear_queue()
        await self.clear_history()
        self._cancellation_token = None
        await self._set_state(ExecutionState.IDLE)
        logger.info("Execution handler reset")


class GCodeExecutionManager:
    """High-level manager for G-code execution with Moonraker integration."""
    
    def __init__(self, moonraker_host: str = 'localhost',
                 moonraker_port: int = 7125,
                 moonraker_api_key: Optional[str] = None,
                 translator_config: Optional[Dict[str, Any]] = None,
                 max_queue_size: int = 1000,
                 max_history_entries: int = 1000,
                 default_timeout: float = 30.0):
        """Initialize G-code execution manager.
        
        Args:
            moonraker_host: Moonraker host address
            moonraker_port: Moonraker port
            moonraker_api_key: Optional API key
            translator_config: Optional translator configuration
            max_queue_size: Maximum queue size
            max_history_entries: Maximum history entries
            default_timeout: Default execution timeout
        """
        self.moonraker_host = moonraker_host
        self.moonraker_port = moonraker_port
        self.moonraker_api_key = moonraker_api_key
        self.default_timeout = default_timeout
        
        # Initialize translator
        self.translator = CommandTranslator(
            config=translator_config,
            moonraker_host=moonraker_host,
            moonraker_port=moonraker_port,
            moonraker_api_key=moonraker_api_key
        )
        
        # Initialize handler (will be created lazily)
        self._handler: Optional[ExecutionHandler] = None
        self._handler_lock = asyncio.Lock()
        
        # Configuration
        self.max_queue_size = max_queue_size
        self.max_history_entries = max_history_entries
        
        logger.info("G-code execution manager initialized")
    
    def _get_handler(self) -> ExecutionHandler:
        """Get or create execution handler.
        
        Returns:
            ExecutionHandler instance
        """
        if self._handler is None:
            moonraker_client = self.translator.get_moonraker_client()
            self._handler = ExecutionHandler(
                moonraker_client=moonraker_client,
                translator=self.translator,
                max_queue_size=self.max_queue_size,
                max_history_entries=self.max_history_entries,
                default_timeout=self.default_timeout
            )
        return self._handler
    
    async def execute(self, gcode: Union[str, List[str]],
                      stop_on_error: bool = True,
                      timeout: Optional[float] = None) -> Union[ExecutionResult, List[ExecutionResult]]:
        """Execute G-code.
        
        Args:
            gcode: G-code string or list of G-code strings
            stop_on_error: Stop on first error
            timeout: Execution timeout
            
        Returns:
            ExecutionResult or list of ExecutionResult objects
        """
        handler = self._get_handler()
        
        if isinstance(gcode, list):
            return await handler.execute_batch(gcode, stop_on_error, timeout)
        else:
            return await handler.execute_single(gcode, timeout)
    
    async def parse_and_execute(self, gcode: Union[str, List[str]],
                               context: Optional[Dict[str, Any]] = None,
                               stop_on_error: bool = True,
                               timeout: Optional[float] = None) -> List[ExecutionResult]:
        """Parse, translate, and execute G-code.
        
        Args:
            gcode: G-code string or list of G-code strings
            context: Optional translation context
            stop_on_error: Stop on first error
            timeout: Execution timeout
            
        Returns:
            List of ExecutionResult objects
        """
        # Parse and translate
        translation_results = self.translator.parse_and_translate(gcode, context)
        
        # Collect all translated G-codes
        all_gcodes = []
        for result in translation_results:
            if result.success:
                all_gcodes.extend(result.translated_commands)
            else:
                if stop_on_error:
                    raise HandlerError(f"Translation failed: {result.error_message}")
        
        # Execute
        handler = self._get_handler()
        return await handler.execute_batch(all_gcodes, stop_on_error, timeout)
    
    async def get_printer_status(self) -> Dict[str, Any]:
        """Get printer status from Moonraker.
        
        Returns:
            Printer status dictionary
        """
        async with self.translator.get_moonraker_client() as client:
            return await client.get_printer_status()
    
    async def get_gcode_store(self) -> Dict[str, Any]:
        """Get G-code store from Moonraker.
        
        Returns:
            G-code store dictionary
        """
        async with self.translator.get_moonraker_client() as client:
            return await client.get_gcode_store()
    
    async def get_klippy_state(self) -> str:
        """Get Klippy connection state.
        
        Returns:
            Klippy state string
        """
        async with self.translator.get_moonraker_client() as client:
            return await client.get_klippy_state()
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics.
        
        Returns:
            Dictionary containing statistics
        """
        handler = self._get_handler()
        return await handler.get_statistics()
    
    async def get_history(self, limit: Optional[int] = None,
                         status: Optional[ExecutionStatus] = None,
                         since: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get execution history.
        
        Args:
            limit: Maximum number of entries
            status: Filter by status
            since: Filter by timestamp
            
        Returns:
            List of history entry dictionaries
        """
        handler = self._get_handler()
        return await handler.get_history(limit, status, since)
    
    async def cancel(self) -> None:
        """Cancel current execution."""
        handler = self._get_handler()
        await handler.cancel_execution()
    
    async def pause(self) -> None:
        """Pause execution."""
        handler = self._get_handler()
        await handler.pause()
    
    async def resume(self) -> None:
        """Resume execution."""
        handler = self._get_handler()
        await handler.resume()
    
    async def reset(self) -> None:
        """Reset execution manager."""
        handler = self._get_handler()
        await handler.reset()
        self.translator.reset_context()
        logger.info("Execution manager reset")


# Convenience functions

async def execute_gcode(gcode: Union[str, List[str]],
                       moonraker_host: str = 'localhost',
                       moonraker_port: int = 7125,
                       moonraker_api_key: Optional[str] = None,
                       timeout: float = 30.0) -> Union[ExecutionResult, List[ExecutionResult]]:
    """Execute G-code with default configuration.
    
    Args:
        gcode: G-code string or list of G-code strings
        moonraker_host: Moonraker host address
        moonraker_port: Moonraker port
        moonraker_api_key: Optional API key
        timeout: Execution timeout
        
    Returns:
        ExecutionResult or list of ExecutionResult objects
    """
    manager = GCodeExecutionManager(
        moonraker_host=moonraker_host,
        moonraker_port=moonraker_port,
        moonraker_api_key=moonraker_api_key,
        default_timeout=timeout
    )
    
    return await manager.execute(gcode)


async def execute_with_translation(gcode: Union[str, List[str]],
                                  context: Optional[Dict[str, Any]] = None,
                                  moonraker_host: str = 'localhost',
                                  moonraker_port: int = 7125,
                                  moonraker_api_key: Optional[str] = None,
                                  timeout: float = 30.0) -> List[ExecutionResult]:
    """Parse, translate, and execute G-code with default configuration.
    
    Args:
        gcode: G-code string or list of G-code strings
        context: Optional translation context
        moonraker_host: Moonraker host address
        moonraker_port: Moonraker port
        moonraker_api_key: Optional API key
        timeout: Execution timeout
        
    Returns:
        List of ExecutionResult objects
    """
    manager = GCodeExecutionManager(
        moonraker_host=moonraker_host,
        moonraker_port=moonraker_port,
        moonraker_api_key=moonraker_api_key,
        default_timeout=timeout
    )
    
    return await manager.parse_and_execute(gcode, context)
