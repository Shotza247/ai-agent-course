from __future__ import annotations

from typing import Any

import requests


RATE_LIMIT_KEYS = {"note", "information"}
RATE_LIMIT_TERMS = {"rate limit", "frequency", "premium", "thank you for using"}


def provider_request_error(
    tool_name: str,
    provider_name: str,
    symbol: str,
    provider_symbol: str,
    exc: requests.RequestException,
) -> dict[str, Any]:
    status = "provider_error"
    response = getattr(exc, "response", None)
    if response is not None and response.status_code == 429:
        status = "rate_limited"

    return {
        "tool_name": tool_name,
        "status": status,
        "summary": (
            f"{provider_name} could not be reached for {symbol}. "
            "The agent will continue with any other available context."
            if status == "provider_error"
            else (
                f"{provider_name} rate limit was reached for {symbol}. "
                "The agent will continue with any cached or other available context."
            )
        ),
        "data": {
            "symbol": symbol,
            "provider_symbol": provider_symbol,
            "error_type": type(exc).__name__,
            "http_status": response.status_code if response is not None else None,
        },
    }


def provider_payload_error(
    tool_name: str,
    provider_name: str,
    symbol: str,
    provider_symbol: str,
    exc: ValueError,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "status": "malformed_response",
        "summary": (
            f"{provider_name} returned an unreadable response for {symbol}. "
            "The agent will continue with any other available context."
        ),
        "data": {
            "symbol": symbol,
            "provider_symbol": provider_symbol,
            "error_type": type(exc).__name__,
        },
    }


def provider_rate_limit(
    tool_name: str,
    provider_name: str,
    symbol: str,
    provider_symbol: str,
    message: str | None = None,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "status": "rate_limited",
        "summary": (
            f"{provider_name} rate limit was reached for {symbol}. "
            "The agent will continue with any cached or other available context."
        ),
        "data": {
            "symbol": symbol,
            "provider_symbol": provider_symbol,
            "provider_message": message,
        },
    }


def rate_limit_message(payload: dict[str, Any]) -> str | None:
    for key, value in payload.items():
        if key.lower() not in RATE_LIMIT_KEYS:
            continue
        message = str(value)
        lowered = message.lower()
        if any(term in lowered for term in RATE_LIMIT_TERMS):
            return message
    return None
