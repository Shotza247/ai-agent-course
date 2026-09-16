from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TraceEvent:
    event_type: str
    agent_name: str
    message: str
    trace_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now_iso)


class EventRecorder:
    """Recorder for agent routing/tool events, with optional JSONL persistence."""

    def __init__(
        self,
        max_events: int = 500,
        enabled: bool = True,
        log_path: str | Path | None = None,
    ) -> None:
        self.max_events = max_events
        self.enabled = enabled
        self.log_path = Path(log_path) if log_path else None
        self._events: list[TraceEvent] = []
        self._lock = Lock()

    def configure(
        self,
        enabled: bool = True,
        log_path: str | Path | None = None,
        max_events: int | None = None,
    ) -> None:
        with self._lock:
            self.enabled = enabled
            self.log_path = Path(log_path) if log_path else None
            if max_events is not None:
                self.max_events = max_events
                self._events = self._events[-self.max_events :]

    def new_trace_id(self) -> str:
        return str(uuid4())

    def record(
        self,
        event_type: str,
        agent_name: str,
        message: str,
        trace_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> TraceEvent:
        event = TraceEvent(
            event_type=event_type,
            agent_name=agent_name,
            message=message,
            trace_id=trace_id,
            metadata=metadata or {},
        )
        if not self.enabled:
            return event

        with self._lock:
            self._events.append(event)
            self._events = self._events[-self.max_events :]
            self._append_event(event)
        return event

    def list_events(self, trace_id: str | None = None) -> list[dict[str, Any]]:
        if not self.enabled:
            return []

        with self._lock:
            if self.log_path:
                event_dicts = self._read_persisted_events()
            else:
                event_dicts = [asdict(event) for event in self._events]

        if trace_id:
            event_dicts = [event for event in event_dicts if event.get("trace_id") == trace_id]
        return event_dicts[-self.max_events :]

    def status(self) -> dict[str, Any]:
        with self._lock:
            event_count = len(self._read_persisted_events()) if self.log_path else len(self._events)
            return {
                "enabled": self.enabled,
                "persistent": self.log_path is not None,
                "log_path": str(self.log_path) if self.log_path else None,
                "max_events": self.max_events,
                "event_count": event_count,
            }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            if self.log_path and self.log_path.exists():
                self.log_path.unlink()

    def _append_event(self, event: TraceEvent) -> None:
        if not self.log_path:
            return

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), default=str) + "\n")

    def _read_persisted_events(self) -> list[dict[str, Any]]:
        if not self.log_path or not self.log_path.exists():
            return []

        events: list[dict[str, Any]] = []
        with self.log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    events.append(payload)
        return events[-self.max_events :]


event_recorder = EventRecorder()
