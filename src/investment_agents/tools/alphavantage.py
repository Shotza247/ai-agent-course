from __future__ import annotations

import requests

from investment_agents.core.config import Settings
from investment_agents.storage.market_cache import MarketDataCache, utc_now_iso
from investment_agents.tools.base import ToolReadiness, ToolResult
from investment_agents.tools.provider_errors import (
    provider_payload_error,
    provider_rate_limit,
    provider_request_error,
    rate_limit_message,
)


class AlphaVantageResearchTool:
    """Alpha Vantage adapter for financial news, sentiment, and macro research."""

    name = "alphavantage_research"
    base_url = "https://www.alphavantage.co/query"

    def __init__(self, settings: Settings, cache: MarketDataCache | None = None) -> None:
        self.settings = settings
        self.cache = cache

    def readiness(self) -> ToolReadiness:
        missing = [] if self.settings.alphavantage_api_key else ["ALPHAVANTAGE_API_KEY"]
        return ToolReadiness(
            tool_name=self.name,
            configured=not missing,
            status="ready" if not missing else "needs_configuration",
            missing_settings=missing,
            capabilities=[
                "news_sentiment",
                "research_headlines",
                "macro_context",
                "event_risk",
                "rate_limit_detection",
                "provider_error_degradation",
                "stale_cache_fallback",
            ],
        )

    def research_symbol(self, symbol: str) -> ToolResult:
        requested_symbol = symbol.upper()
        provider_symbol = self._provider_symbol(requested_symbol)
        readiness = self.readiness()
        if not readiness.configured:
            return ToolResult(
                tool_name=self.name,
                status=readiness.status,
                summary=(
                    "Alpha Vantage access is not configured yet. Missing settings: "
                    f"{', '.join(readiness.missing_settings)}."
                ),
                data={
                    "symbol": requested_symbol,
                    "provider_symbol": provider_symbol,
                    "missing_settings": readiness.missing_settings,
                },
            )

        cache_key = provider_symbol.upper()
        cached = None
        if self.cache:
            cached = self.cache.get_fresh_raw_payload(
                source=self.name,
                endpoint="news_sentiment",
                cache_key=cache_key,
                ttl_seconds=self.settings.market_cache_ttl_seconds,
            )

        if cached:
            payload = cached.payload
            cache_status = "hit"
            fetched_at = cached.fetched_at
        else:
            try:
                response = requests.get(
                    self.base_url,
                    params={
                        "function": "NEWS_SENTIMENT",
                        "tickers": provider_symbol,
                        "apikey": self.settings.alphavantage_api_key,
                    },
                    timeout=(3.05, self.settings.provider_request_timeout_seconds),
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                error_result = ToolResult(
                    **provider_request_error(
                        tool_name=self.name,
                        provider_name="Alpha Vantage",
                        symbol=requested_symbol,
                        provider_symbol=provider_symbol,
                        exc=exc,
                    )
                )
                return self._stale_research_result_or_error(
                    error_result,
                    requested_symbol,
                    provider_symbol,
                    cache_key,
                )

            try:
                payload = response.json()
            except ValueError as exc:
                error_result = ToolResult(
                    **provider_payload_error(
                        tool_name=self.name,
                        provider_name="Alpha Vantage",
                        symbol=requested_symbol,
                        provider_symbol=provider_symbol,
                        exc=exc,
                    )
                )
                return self._stale_research_result_or_error(
                    error_result,
                    requested_symbol,
                    provider_symbol,
                    cache_key,
                )
            if not isinstance(payload, dict):
                error_result = ToolResult(
                    **provider_payload_error(
                        tool_name=self.name,
                        provider_name="Alpha Vantage",
                        symbol=requested_symbol,
                        provider_symbol=provider_symbol,
                        exc=ValueError("Expected a JSON object."),
                    )
                )
                return self._stale_research_result_or_error(
                    error_result,
                    requested_symbol,
                    provider_symbol,
                    cache_key,
                )
            limit_message = rate_limit_message(payload)
            if limit_message:
                error_result = ToolResult(
                    **provider_rate_limit(
                        tool_name=self.name,
                        provider_name="Alpha Vantage",
                        symbol=requested_symbol,
                        provider_symbol=provider_symbol,
                        message=limit_message,
                    )
                )
                return self._stale_research_result_or_error(
                    error_result,
                    requested_symbol,
                    provider_symbol,
                    cache_key,
                )
            cache_status = "miss"
            fetched_at = utc_now_iso()
            if self.cache:
                stored = self.cache.store_raw_payload(
                    self.name,
                    "news_sentiment",
                    cache_key,
                    payload,
                    fetched_at=fetched_at,
                )
                fetched_at = stored.fetched_at

        if not isinstance(payload, dict):
            error_result = ToolResult(
                **provider_payload_error(
                    tool_name=self.name,
                    provider_name="Alpha Vantage",
                    symbol=requested_symbol,
                    provider_symbol=provider_symbol,
                    exc=ValueError("Expected a JSON object."),
                )
            )
            return self._stale_research_result_or_error(
                error_result,
                requested_symbol,
                provider_symbol,
                cache_key,
            )
        feed_payload = payload.get("feed", [])
        if not isinstance(feed_payload, list):
            error_result = ToolResult(
                **provider_payload_error(
                    tool_name=self.name,
                    provider_name="Alpha Vantage",
                    symbol=requested_symbol,
                    provider_symbol=provider_symbol,
                    exc=ValueError("Expected feed to be a list."),
                )
            )
            return self._stale_research_result_or_error(
                error_result,
                requested_symbol,
                provider_symbol,
                cache_key,
            )
        feed = feed_payload[:5]
        titles = [
            item.get("title", "Untitled") if isinstance(item, dict) else "Untitled"
            for item in feed
        ]
        if self.cache:
            self.cache.store_curated_snapshot(
                self.name,
                "news_sentiment",
                cache_key,
                {
                    "symbol": requested_symbol,
                    "provider_symbol": provider_symbol,
                    "headlines": titles,
                    "fetched_at": fetched_at,
                },
            )
        symbol_text = (
            f"{requested_symbol} ({provider_symbol})"
            if requested_symbol != provider_symbol
            else requested_symbol
        )
        return ToolResult(
            tool_name=self.name,
            summary=f"Alpha Vantage returned {len(feed)} recent research/news items for {symbol_text}.",
            data={
                "symbol": requested_symbol,
                "provider_symbol": provider_symbol,
                "headlines": titles,
                "raw": payload,
                "cache_status": cache_status,
                "fetched_at": fetched_at,
            },
        )

    def _provider_symbol(self, symbol: str) -> str:
        return (self.settings.alphavantage_symbol_aliases or {}).get(symbol, symbol)

    def _stale_research_result_or_error(
        self,
        error_result: ToolResult,
        requested_symbol: str,
        provider_symbol: str,
        cache_key: str,
    ) -> ToolResult:
        if not self.cache:
            return error_result

        cached = self.cache.get_latest_raw_payload(
            source=self.name,
            endpoint="news_sentiment",
            cache_key=cache_key,
        )
        if not cached or not isinstance(cached.payload, dict):
            return error_result

        feed_payload = cached.payload.get("feed", [])
        if not isinstance(feed_payload, list):
            return error_result

        feed = feed_payload[:5]
        titles = [
            item.get("title", "Untitled") if isinstance(item, dict) else "Untitled"
            for item in feed
        ]
        symbol_text = (
            f"{requested_symbol} ({provider_symbol})"
            if requested_symbol != provider_symbol
            else requested_symbol
        )
        return ToolResult(
            tool_name=self.name,
            status="stale_cache",
            summary=(
                f"Alpha Vantage is currently unavailable for {symbol_text}; using "
                f"{len(feed)} stale cached research/news items from {cached.fetched_at}."
            ),
            data={
                "symbol": requested_symbol,
                "provider_symbol": provider_symbol,
                "headlines": titles,
                "raw": cached.payload,
                "cache_status": "stale",
                "fetched_at": cached.fetched_at,
                "stale_fetched_at": cached.fetched_at,
                "degraded_from": {
                    "status": error_result.status,
                    "summary": error_result.summary,
                    "data": error_result.data,
                },
            },
        )
