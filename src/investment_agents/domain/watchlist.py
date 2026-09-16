from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

from investment_agents.domain.money import (
    DEFAULT_CURRENCY,
    normalize_currency,
    optional_decimal,
)


HEADER_ALIASES = {
    "symbol": {"symbol", "ticker", "asset", "instrument"},
    "name": {"name", "company", "security", "holding"},
    "currency": {"currency", "ccy"},
    "market": {"market", "exchange", "venue"},
    "target_price": {"target price", "target", "watch price", "buy below"},
    "current_price": {"current price", "market price", "last price", "price"},
    "status": {"status", "watch status", "state"},
    "reason": {"reason", "notes", "thesis", "why", "comment"},
}


@dataclass(frozen=True)
class WatchlistItem:
    symbol: str
    currency: str = DEFAULT_CURRENCY
    name: str | None = None
    market: str | None = None
    target_price: Decimal | None = None
    current_price: Decimal | None = None
    status: str | None = None
    reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ["target_price", "current_price"]:
            if payload[key] is not None:
                payload[key] = str(payload[key])
        return payload


@dataclass(frozen=True)
class WatchlistSummary:
    item_count: int
    symbols: list[str]
    currencies: list[str]
    markets: list[str]
    by_status: dict[str, int]
    items: list[WatchlistItem]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_count": self.item_count,
            "symbols": self.symbols,
            "currencies": self.currencies,
            "markets": self.markets,
            "by_status": self.by_status,
            "items": [item.to_dict() for item in self.items],
            "warnings": self.warnings,
        }

    def to_summary_text(self) -> str:
        if self.item_count == 0:
            return "No watchlist items were found."

        market_text = ", ".join(self.markets) if self.markets else "unknown markets"
        status_text = ", ".join(
            f"{status}: {count}"
            for status, count in self.by_status.items()
        )
        return (
            f"Watchlist contains {self.item_count} items across {market_text}. "
            f"Symbols: {', '.join(self.symbols)}. Status split: {status_text}."
        )


def parse_watchlist_rows(rows: list[list[Any]]) -> tuple[list[WatchlistItem], list[str]]:
    if not rows:
        return [], ["Watchlist sheet returned no rows."]

    header = [_normalize_header(value) for value in rows[0]]
    column_map = _build_column_map(header)
    if "symbol" not in column_map:
        return [], ["Watchlist sheet is missing required column: symbol."]

    items: list[WatchlistItem] = []
    warnings: list[str] = []
    for index, row in enumerate(rows[1:], start=2):
        raw = _row_to_dict(header, row)
        symbol = _get_value(row, column_map, "symbol").upper()
        if not symbol:
            warnings.append(f"Skipped row {index}: missing symbol.")
            continue

        items.append(
            WatchlistItem(
                symbol=symbol,
                currency=normalize_currency(_get_value(row, column_map, "currency")),
                name=_optional_text(_get_value(row, column_map, "name")),
                market=_optional_text(_get_value(row, column_map, "market")),
                target_price=optional_decimal(_get_value(row, column_map, "target_price")),
                current_price=optional_decimal(_get_value(row, column_map, "current_price")),
                status=_optional_text(_get_value(row, column_map, "status")),
                reason=_optional_text(_get_value(row, column_map, "reason")),
                raw=raw,
            )
        )

    return items, warnings


def summarize_watchlist(
    items: list[WatchlistItem],
    warnings: list[str] | None = None,
) -> WatchlistSummary:
    return WatchlistSummary(
        item_count=len(items),
        symbols=sorted({item.symbol for item in items}),
        currencies=sorted({item.currency for item in items}),
        markets=sorted({item.market for item in items if item.market}),
        by_status=_count_by_status(items),
        items=sorted(items, key=lambda item: item.symbol),
        warnings=warnings or [],
    )


def _count_by_status(items: list[WatchlistItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        status = item.status or "unspecified"
        counts.setdefault(status, 0)
        counts[status] += 1
    return dict(sorted(counts.items()))


def _build_column_map(headers: list[str]) -> dict[str, int]:
    column_map: dict[str, int] = {}
    for index, header in enumerate(headers):
        for canonical, aliases in HEADER_ALIASES.items():
            if header in aliases and canonical not in column_map:
                column_map[canonical] = index
    return column_map


def _row_to_dict(headers: list[str], row: list[Any]) -> dict[str, Any]:
    return {
        header or f"column_{index + 1}": row[index] if index < len(row) else ""
        for index, header in enumerate(headers)
    }


def _get_value(row: list[Any], column_map: dict[str, int], name: str) -> str:
    index = column_map.get(name)
    if index is None or index >= len(row):
        return ""
    return str(row[index]).strip()


def _optional_text(value: str) -> str | None:
    return value or None


def _normalize_header(value: Any) -> str:
    return str(value).strip().lower()
