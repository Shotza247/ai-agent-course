from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


ATTENTION_STATUSES = {
    "malformed_response",
    "needs_configuration",
    "needs_symbol",
    "provider_error",
    "rate_limited",
    "stale_cache",
}


def portfolio_alert_rows(agent_results: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in agent_results:
        metadata = result.get("metadata") or {}
        portfolio_summary = metadata.get("portfolio_summary") or {}
        for alert in portfolio_summary.get("alerts") or []:
            rows.append(
                {
                    "severity": str(alert.get("severity", "")),
                    "type": str(alert.get("alert_type", "")).replace("_", " "),
                    "symbol": str(alert.get("symbol", "")),
                    "currency": str(alert.get("currency", "")),
                    "value": _ratio_to_percent(alert.get("value")),
                    "threshold": _ratio_to_percent(alert.get("threshold")),
                    "message": str(alert.get("message", "")),
                }
            )
    return rows


def data_source_status_rows(agent_results: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in agent_results:
        agent_name = str(result.get("agent_name", ""))
        tool_calls = result.get("tool_calls") or []
        if tool_calls:
            for tool_call in tool_calls:
                rows.append(_tool_status_row(agent_name, tool_call))
            continue

        metadata = result.get("metadata") or {}
        tool_status = metadata.get("tool_status")
        if tool_status:
            symbols = metadata.get("symbols") or []
            rows.append(
                {
                    "agent": agent_name,
                    "tool": "",
                    "symbol": ", ".join(str(symbol) for symbol in symbols),
                    "provider_symbol": "",
                    "status": _status_label(tool_status),
                    "cache": "",
                    "source_at": "",
                    "stale_at": "",
                    "degraded_from": "",
                    "summary": str(result.get("summary", "")),
                }
            )
    return rows


def data_source_attention_count(rows: list[dict[str, str]]) -> int:
    return sum(1 for row in rows if row.get("status", "").replace(" ", "_") in ATTENTION_STATUSES)


def source_note_rows(source_notes: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "agent": str(note.get("agent_name", "")),
            "tool": str(note.get("tool_name", "")),
            "symbol": _symbol_text(note),
            "status": _status_label(note.get("status", "")),
            "cache": str(note.get("cache_status", "")),
            "source_at": str(note.get("fetched_at", "") or note.get("stale_fetched_at", "")),
            "stale_at": str(note.get("stale_fetched_at", "")),
            "degraded_from": _status_label(note.get("degraded_from_status", "")),
            "message": str(note.get("message", "")),
        }
        for note in source_notes
    ]


def _ratio_to_percent(value: Any) -> str:
    try:
        return f"{(Decimal(str(value)) * Decimal('100')).quantize(Decimal('0.1'))}%"
    except (InvalidOperation, TypeError, ValueError):
        return str(value or "")


def _tool_status_row(agent_name: str, tool_call: dict[str, Any]) -> dict[str, str]:
    data = tool_call.get("data") or {}
    degraded_from = data.get("degraded_from") or {}
    degraded_status = degraded_from.get("status", "") if isinstance(degraded_from, dict) else ""
    return {
        "agent": agent_name,
        "tool": str(tool_call.get("tool_name", "")),
        "symbol": str(data.get("symbol", "")),
        "provider_symbol": str(data.get("provider_symbol", "")),
        "status": _status_label(tool_call.get("status", "")),
        "cache": str(data.get("cache_status", "")),
        "source_at": str(data.get("fetched_at", "") or data.get("stale_fetched_at", "")),
        "stale_at": str(data.get("stale_fetched_at", "")),
        "degraded_from": _status_label(degraded_status),
        "summary": str(tool_call.get("summary", "")),
    }


def _status_label(status: Any) -> str:
    return str(status or "").replace("_", " ")


def _symbol_text(note: dict[str, Any]) -> str:
    symbol = str(note.get("symbol", ""))
    provider_symbol = str(note.get("provider_symbol", ""))
    if symbol and provider_symbol and symbol != provider_symbol:
        return f"{symbol} ({provider_symbol})"
    return symbol or provider_symbol


def event_table_rows(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for event in events:
        metadata = event.get("metadata") or {}
        rows.append(
            {
                "time": str(event.get("timestamp", "")),
                "event": str(event.get("event_type", "")),
                "agent": str(event.get("agent_name", "")),
                "message": str(event.get("message", "")),
                "tool": str(metadata.get("tool_name", "")),
                "status": str(metadata.get("status", "")),
            }
        )
    return rows


def trace_metrics(events: list[dict[str, Any]]) -> dict[str, int]:
    agents = {
        str(event.get("agent_name", ""))
        for event in events
        if event.get("agent_name")
    }
    tools = {
        str((event.get("metadata") or {}).get("tool_name", ""))
        for event in events
        if (event.get("metadata") or {}).get("tool_name")
    }
    return {
        "events": len(events),
        "agents": len(agents),
        "tools": len(tools),
    }
