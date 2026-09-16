from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    tool_name: str
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    status: str = "ok"


@dataclass(frozen=True)
class ToolReadiness:
    tool_name: str
    configured: bool
    status: str
    missing_settings: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)


class ToolError(RuntimeError):
    """Raised when a tool cannot complete its requested data fetch."""
