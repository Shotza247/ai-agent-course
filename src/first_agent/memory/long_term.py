from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True)
class MemoryRecord:
    namespace: tuple[str, ...]
    kind: str
    value: dict[str, object]
    memory_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class InMemoryLongTermMemory:
    """Small explicit store for reusable preferences and saved research metadata."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, ...], dict[str, MemoryRecord]] = {}

    def put(self, record: MemoryRecord) -> None:
        self._records.setdefault(record.namespace, {})[record.memory_id] = record

    def list(self, namespace: tuple[str, ...]) -> list[MemoryRecord]:
        return list(self._records.get(namespace, {}).values())

    def delete(self, namespace: tuple[str, ...], memory_id: str) -> None:
        records = self._records.get(namespace)
        if records:
            records.pop(memory_id, None)
