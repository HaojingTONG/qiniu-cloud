"""
Event Bus for Voice OS UI.
Enables real-time communication between backend and frontend.
"""
import logging
import queue
import threading
from typing import Dict, Any, List, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class Event:
    """Event object containing type and data."""

    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.type = event_type
        self.data = data
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp
        }


class EventBus:
    """
    Simple event bus for publishing and subscribing to events.
    Thread-safe implementation for real-time UI updates.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_queue: queue.Queue = queue.Queue(maxsize=1000)
        self._lock = threading.Lock()
        self._confirmation_event = threading.Event()
        self._confirmation_result = None
        self._continue_event = threading.Event()
        self._continue_result = None
        logger.info("EventBus initialized")

    def subscribe(self, event_type: str, callback: Callable[[Event], None]):
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to (e.g., "asr_start", "intent_parsed")
            callback: Function to call when event is published
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type}")

    def publish(self, event_type: str, data: Dict[str, Any]):
        """
        Publish an event to all subscribers.

        Args:
            event_type: Type of event
            data: Event data
        """
        event = Event(event_type, data)

        # Add to queue for SSE
        try:
            self._event_queue.put_nowait(event)
        except queue.Full:
            logger.warning("Event queue full, dropping oldest event")
            try:
                self._event_queue.get_nowait()
                self._event_queue.put_nowait(event)
            except:
                pass

        # Notify subscribers
        with self._lock:
            subscribers = self._subscribers.get(event_type, [])

        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")

    def get_events(self) -> List[Event]:
        """Get all pending events (for SSE)."""
        events = []
        while not self._event_queue.empty():
            try:
                events.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def clear(self):
        """Clear all pending events."""
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except queue.Empty:
                break

    def wait_for_confirmation(self, timeout: float = 300.0) -> bool:
        """
        Wait for user confirmation from Web UI.

        Args:
            timeout: Maximum time to wait in seconds (default: 5 minutes)

        Returns:
            True if confirmed, False if cancelled or timeout
        """
        # Clear previous confirmation
        self._confirmation_event.clear()
        self._confirmation_result = None

        # Wait for confirmation
        logger.info(f"Waiting for user confirmation (timeout: {timeout}s)...")
        result = self._confirmation_event.wait(timeout=timeout)

        if not result:
            logger.warning("Confirmation timeout")
            return False

        confirmed = self._confirmation_result
        logger.info(f"Confirmation received: {confirmed}")
        return confirmed

    def set_confirmation(self, confirmed: bool):
        """
        Set confirmation result (called from Web UI).

        Args:
            confirmed: True if user confirmed, False if cancelled
        """
        self._confirmation_result = confirmed
        self._confirmation_event.set()
        logger.info(f"Confirmation set to: {confirmed}")

    def wait_for_continue(self, timeout: float = 600.0) -> bool:
        """
        Wait for user to click continue button from Web UI.

        Args:
            timeout: Maximum time to wait in seconds (default: 10 minutes)

        Returns:
            True if user clicked continue, False if timeout
        """
        # Clear previous state
        self._continue_event.clear()
        self._continue_result = None

        # Wait for continue
        logger.info(f"Waiting for user to continue (timeout: {timeout}s)...")
        result = self._continue_event.wait(timeout=timeout)

        if not result:
            logger.warning("Continue timeout")
            return False

        should_continue = self._continue_result
        logger.info(f"Continue received: {should_continue}")
        return should_continue

    def set_continue(self, should_continue: bool):
        """
        Set continue result (called from Web UI).

        Args:
            should_continue: True if user wants to continue, False to stop
        """
        self._continue_result = should_continue
        self._continue_event.set()
        logger.info(f"Continue set to: {should_continue}")


# Global event bus instance
_event_bus: EventBus = None


def get_event_bus() -> EventBus:
    """Get or create global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# Event type constants
class EventType:
    """Standard event types for Voice OS."""

    # ASR events
    ASR_START = "asr_start"
    ASR_COMPLETE = "asr_complete"
    ASR_ERROR = "asr_error"

    # Planning events
    PLANNING_START = "planning_start"
    INTENT_PARSED = "intent_parsed"
    PLAN_PARSED = "plan_parsed"
    PLANNING_ERROR = "planning_error"

    # Execution events
    EXECUTION_START = "execution_start"
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    STEP_ERROR = "step_error"
    EXECUTION_COMPLETE = "execution_complete"
    INTENT_COMPLETE = "intent_complete"  # Single intent execution complete

    # Confirmation events
    CONFIRMATION_REQUIRED = "confirmation_required"
    CONFIRMATION_RESULT = "confirmation_result"

    # Continue events
    READY_FOR_NEXT = "ready_for_next"
    CONTINUE_RESULT = "continue_result"

    # TTS events
    TTS_START = "tts_start"
    TTS_COMPLETE = "tts_complete"

    # System events
    SYSTEM_READY = "system_ready"
    SYSTEM_ERROR = "system_error"
