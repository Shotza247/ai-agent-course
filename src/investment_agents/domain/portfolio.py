from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Mapping

from investment_agents.domain.money import (
    DEFAULT_CURRENCY,
    decimal_or_zero,
    normalize_currency,
    optional_decimal,
)


HEADER_ALIASES = {
    "symbol": {"symbol", "ticker", "asset", "instrument"},
    "name": {"name", "company", "security", "holding"},
    "quantity": {"quantity", "qty", "shares", "shares held", "units"},
    "current_price": {"current price", "market price", "last price", "price"},
    "purchase_value": {"purchase value", "cost basis", "book cost", "cost", "invested value"},
    "current_value": {"current value", "market value", "holding value", "value"},
    "unrealized_pl": {"p/l", "pl", "$ p/l", "profit/loss", "gain/loss", "unrealized p/l"},
    "profit_status": {"profit status", "status"},
    "currency": {"currency", "ccy"},
    "market": {"market", "exchange", "venue"},
}

CONCENTRATION_WARNING_THRESHOLD = Decimal("0.40")
LOSS_ALERT_THRESHOLD = Decimal("0.10")


@dataclass(frozen=True)
class PortfolioHolding:
    symbol: str
    quantity: Decimal
    currency: str = DEFAULT_CURRENCY
    name: str | None = None
    current_price: Decimal | None = None
    purchase_value: Decimal | None = None
    current_value: Decimal | None = None
    unrealized_pl: Decimal | None = None
    profit_status: str | None = None
    market: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ["quantity", "current_price", "purchase_value", "current_value", "unrealized_pl"]:
            if payload[key] is not None:
                payload[key] = str(payload[key])
        return payload


@dataclass(frozen=True)
class PortfolioAllocation:
    symbol: str
    currency: str
    current_value: Decimal
    weight: Decimal
    reporting_value: Decimal | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "currency": self.currency,
            "current_value": str(self.current_value),
            "weight": str(self.weight),
            "reporting_value": str(self.reporting_value) if self.reporting_value is not None else None,
        }


@dataclass(frozen=True)
class PortfolioAlert:
    alert_type: str
    severity: str
    symbol: str
    currency: str
    message: str
    value: Decimal
    threshold: Decimal

    def to_dict(self) -> dict[str, str]:
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "symbol": self.symbol,
            "currency": self.currency,
            "message": self.message,
            "value": str(self.value),
            "threshold": str(self.threshold),
        }


@dataclass(frozen=True)
class PortfolioSummary:
    holding_count: int
    symbols: list[str]
    currencies: list[str]
    total_current_value_by_currency: dict[str, Decimal]
    total_purchase_value_by_currency: dict[str, Decimal]
    total_unrealized_pl_by_currency: dict[str, Decimal]
    allocations_by_currency: list[PortfolioAllocation]
    concentration_warnings: list[str] = field(default_factory=list)
    alerts: list[PortfolioAlert] = field(default_factory=list)
    reporting_currency: str | None = None
    total_current_value_reporting_currency: Decimal | None = None
    total_purchase_value_reporting_currency: Decimal | None = None
    total_unrealized_pl_reporting_currency: Decimal | None = None
    allocations_reporting_currency: list[PortfolioAllocation] = field(default_factory=list)
    fx_rates_used: dict[str, Decimal] = field(default_factory=dict)
    missing_fx_rates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "holding_count": self.holding_count,
            "symbols": self.symbols,
            "currencies": self.currencies,
            "total_current_value_by_currency": _stringify_amounts(self.total_current_value_by_currency),
            "total_purchase_value_by_currency": _stringify_amounts(self.total_purchase_value_by_currency),
            "total_unrealized_pl_by_currency": _stringify_amounts(self.total_unrealized_pl_by_currency),
            "allocations_by_currency": [
                allocation.to_dict() for allocation in self.allocations_by_currency
            ],
            "concentration_warnings": self.concentration_warnings,
            "alerts": [alert.to_dict() for alert in self.alerts],
            "reporting_currency": self.reporting_currency,
            "total_current_value_reporting_currency": (
                str(self.total_current_value_reporting_currency)
                if self.total_current_value_reporting_currency is not None
                else None
            ),
            "total_purchase_value_reporting_currency": (
                str(self.total_purchase_value_reporting_currency)
                if self.total_purchase_value_reporting_currency is not None
                else None
            ),
            "total_unrealized_pl_reporting_currency": (
                str(self.total_unrealized_pl_reporting_currency)
                if self.total_unrealized_pl_reporting_currency is not None
                else None
            ),
            "allocations_reporting_currency": [
                allocation.to_dict() for allocation in self.allocations_reporting_currency
            ],
            "fx_rates_used": _stringify_amounts(self.fx_rates_used),
            "missing_fx_rates": self.missing_fx_rates,
            "warnings": self.warnings,
        }

    def to_summary_text(self) -> str:
        if self.holding_count == 0:
            return "No portfolio holdings were found."

        current_value_text = ", ".join(
            f"{currency} {amount}"
            for currency, amount in self.total_current_value_by_currency.items()
        )
        pl_text = ", ".join(
            f"{currency} {amount}"
            for currency, amount in self.total_unrealized_pl_by_currency.items()
        )
        concentration_text = " ".join(self.concentration_warnings)
        reporting_text = ""
        if self.reporting_currency and self.total_current_value_reporting_currency is not None:
            reporting_text = (
                f" Reporting value: {self.reporting_currency} "
                f"{self.total_current_value_reporting_currency}; reporting P/L: "
                f"{self.reporting_currency} {self.total_unrealized_pl_reporting_currency}."
            )
        elif self.reporting_currency and self.missing_fx_rates:
            reporting_text = (
                f" Reporting totals need FX rates for: "
                f"{', '.join(self.missing_fx_rates)}."
            )

        return (
            f"Portfolio snapshot contains {self.holding_count} holdings across "
            f"{len(self.currencies)} currencies. Current value by currency: "
            f"{current_value_text}; P/L by currency: {pl_text}.{reporting_text} "
            f"{concentration_text}".strip()
        )


def parse_holding_rows(rows: list[list[Any]]) -> tuple[list[PortfolioHolding], list[str]]:
    if not rows:
        return [], ["Holdings sheet returned no rows."]

    header = [_normalize_header(value) for value in rows[0]]
    column_map = _build_column_map(header)
    warnings: list[str] = []

    required = ["symbol", "quantity"]
    missing = [name for name in required if name not in column_map]
    if missing:
        return [], [f"Holdings sheet is missing required columns: {', '.join(missing)}."]

    snapshot_columns = {"current_value", "purchase_value", "unrealized_pl", "profit_status"}
    if not snapshot_columns.intersection(column_map):
        return [], [
            "Holdings sheet is missing snapshot value columns: "
            "current_value, purchase_value, unrealized_pl, or profit_status."
        ]

    holdings: list[PortfolioHolding] = []
    for index, row in enumerate(rows[1:], start=2):
        raw = _row_to_dict(header, row)
        symbol = _get_value(row, column_map, "symbol").upper()
        quantity = decimal_or_zero(_get_value(row, column_map, "quantity"))
        current_price = optional_decimal(_get_value(row, column_map, "current_price"))
        purchase_value = optional_decimal(_get_value(row, column_map, "purchase_value"))
        current_value = optional_decimal(_get_value(row, column_map, "current_value"))
        unrealized_pl = optional_decimal(_get_value(row, column_map, "unrealized_pl"))
        currency = normalize_currency(_get_value(row, column_map, "currency"))

        if not symbol or quantity == 0:
            warnings.append(f"Skipped row {index}: missing symbol or quantity.")
            continue

        if current_value is None and current_price is not None:
            current_value = quantity * current_price
        if unrealized_pl is None and current_value is not None and purchase_value is not None:
            unrealized_pl = current_value - purchase_value

        if current_value is None:
            warnings.append(f"Row {index}: current value could not be calculated.")

        holdings.append(
            PortfolioHolding(
                symbol=symbol,
                quantity=quantity,
                currency=currency,
                name=_optional_text(_get_value(row, column_map, "name")),
                current_price=current_price,
                purchase_value=purchase_value,
                current_value=current_value,
                unrealized_pl=unrealized_pl,
                profit_status=_optional_text(_get_value(row, column_map, "profit_status")),
                market=_optional_text(_get_value(row, column_map, "market")),
                raw=raw,
            )
        )

    return holdings, warnings


def summarize_holdings(
    holdings: list[PortfolioHolding],
    warnings: list[str] | None = None,
    reporting_currency: str | None = None,
    fx_rates: Mapping[str, str | Decimal] | None = None,
    concentration_alert_threshold: Decimal = CONCENTRATION_WARNING_THRESHOLD,
    loss_alert_threshold: Decimal = LOSS_ALERT_THRESHOLD,
) -> PortfolioSummary:
    holdings_with_value = [
        holding for holding in holdings if holding.current_value is not None
    ]
    current_value_by_currency = _sum_optional_by_currency(holdings, "current_value")
    purchase_value_by_currency = _sum_optional_by_currency(holdings, "purchase_value")
    unrealized_pl_by_currency = _sum_optional_by_currency(holdings, "unrealized_pl")
    allocations_by_currency = _allocations_by_currency(holdings_with_value)
    alerts = _portfolio_alerts(
        holdings=holdings,
        allocations=allocations_by_currency,
        concentration_alert_threshold=concentration_alert_threshold,
        loss_alert_threshold=loss_alert_threshold,
    )
    concentration_warnings = [
        alert.message
        for alert in alerts
        if alert.alert_type == "concentration"
    ]
    normalized = _normalize_holdings(
        holdings_with_value,
        purchase_value_by_currency,
        unrealized_pl_by_currency,
        reporting_currency,
        fx_rates or {},
    )

    return PortfolioSummary(
        holding_count=len(holdings),
        symbols=sorted({holding.symbol for holding in holdings}),
        currencies=sorted({holding.currency for holding in holdings}),
        total_current_value_by_currency=current_value_by_currency,
        total_purchase_value_by_currency=purchase_value_by_currency,
        total_unrealized_pl_by_currency=unrealized_pl_by_currency,
        allocations_by_currency=allocations_by_currency,
        concentration_warnings=concentration_warnings,
        alerts=alerts,
        reporting_currency=normalized["reporting_currency"],
        total_current_value_reporting_currency=normalized["total_current_value_reporting_currency"],
        total_purchase_value_reporting_currency=normalized["total_purchase_value_reporting_currency"],
        total_unrealized_pl_reporting_currency=normalized["total_unrealized_pl_reporting_currency"],
        allocations_reporting_currency=normalized["allocations_reporting_currency"],
        fx_rates_used=normalized["fx_rates_used"],
        missing_fx_rates=normalized["missing_fx_rates"],
        warnings=warnings or [],
    )


def _normalize_holdings(
    holdings: list[PortfolioHolding],
    purchase_value_by_currency: dict[str, Decimal],
    unrealized_pl_by_currency: dict[str, Decimal],
    reporting_currency: str | None,
    fx_rates: Mapping[str, str | Decimal],
) -> dict[str, Any]:
    if not reporting_currency:
        return _empty_normalization(None)

    normalized_reporting_currency = normalize_currency(reporting_currency)
    currencies = sorted(
        {holding.currency for holding in holdings}
        | set(purchase_value_by_currency)
        | set(unrealized_pl_by_currency)
    )
    rates_used: dict[str, Decimal] = {}
    missing_rates: list[str] = []
    for currency in currencies:
        if currency == normalized_reporting_currency:
            rates_used[currency] = Decimal("1")
            continue
        rate = optional_decimal(str(fx_rates.get(currency, "")))
        if rate is None:
            missing_rates.append(f"{currency}->{normalized_reporting_currency}")
            continue
        rates_used[currency] = rate

    if missing_rates:
        result = _empty_normalization(normalized_reporting_currency)
        result["fx_rates_used"] = rates_used
        result["missing_fx_rates"] = missing_rates
        return result

    reporting_values = [
        (
            holding.symbol,
            holding.current_value * rates_used[holding.currency],
        )
        for holding in holdings
        if holding.current_value is not None
    ]
    total_current_value = sum((value for _symbol, value in reporting_values), Decimal("0"))
    allocations_reporting_currency = [
        PortfolioAllocation(
            symbol=symbol,
            currency=normalized_reporting_currency,
            current_value=value,
            reporting_value=value,
            weight=_safe_weight(value, total_current_value),
        )
        for symbol, value in sorted(reporting_values, key=lambda item: item[1], reverse=True)
    ]

    return {
        "reporting_currency": normalized_reporting_currency,
        "total_current_value_reporting_currency": total_current_value,
        "total_purchase_value_reporting_currency": _apply_rates(purchase_value_by_currency, rates_used),
        "total_unrealized_pl_reporting_currency": _apply_rates(unrealized_pl_by_currency, rates_used),
        "allocations_reporting_currency": allocations_reporting_currency,
        "fx_rates_used": rates_used,
        "missing_fx_rates": [],
    }


def _empty_normalization(reporting_currency: str | None) -> dict[str, Any]:
    return {
        "reporting_currency": reporting_currency,
        "total_current_value_reporting_currency": None,
        "total_purchase_value_reporting_currency": None,
        "total_unrealized_pl_reporting_currency": None,
        "allocations_reporting_currency": [],
        "fx_rates_used": {},
        "missing_fx_rates": [],
    }


def _allocations_by_currency(holdings: list[PortfolioHolding]) -> list[PortfolioAllocation]:
    totals = _sum_optional_by_currency(holdings, "current_value")
    allocations = []
    for holding in holdings:
        if holding.current_value is None:
            continue
        allocations.append(
            PortfolioAllocation(
                symbol=holding.symbol,
                currency=holding.currency,
                current_value=holding.current_value,
                weight=_safe_weight(holding.current_value, totals[holding.currency]),
            )
        )
    return sorted(allocations, key=lambda allocation: (allocation.currency, -allocation.weight))


def _portfolio_alerts(
    holdings: list[PortfolioHolding],
    allocations: list[PortfolioAllocation],
    concentration_alert_threshold: Decimal,
    loss_alert_threshold: Decimal,
) -> list[PortfolioAlert]:
    alerts = []
    for allocation in allocations:
        if allocation.weight >= concentration_alert_threshold:
            percent = (allocation.weight * Decimal("100")).quantize(Decimal("0.1"))
            threshold_percent = (
                concentration_alert_threshold * Decimal("100")
            ).quantize(Decimal("0.1"))
            alerts.append(
                PortfolioAlert(
                    alert_type="concentration",
                    severity="warning",
                    symbol=allocation.symbol,
                    currency=allocation.currency,
                    value=allocation.weight,
                    threshold=concentration_alert_threshold,
                    message=(
                        f"{allocation.symbol} is {percent}% of the {allocation.currency} "
                        f"slice, above the {threshold_percent}% threshold."
                    ),
                )
            )

    for holding in holdings:
        if holding.purchase_value is None or holding.purchase_value <= 0:
            continue
        if holding.unrealized_pl is None or holding.unrealized_pl >= 0:
            continue
        loss_ratio = abs(holding.unrealized_pl) / holding.purchase_value
        if loss_ratio >= loss_alert_threshold:
            percent = (loss_ratio * Decimal("100")).quantize(Decimal("0.1"))
            threshold_percent = (loss_alert_threshold * Decimal("100")).quantize(Decimal("0.1"))
            alerts.append(
                PortfolioAlert(
                    alert_type="loss_threshold",
                    severity="warning",
                    symbol=holding.symbol,
                    currency=holding.currency,
                    value=loss_ratio,
                    threshold=loss_alert_threshold,
                    message=(
                        f"{holding.symbol} is down {percent}% in {holding.currency}, "
                        f"above the {threshold_percent}% loss threshold."
                    ),
                )
            )
    return sorted(alerts, key=lambda alert: (alert.alert_type, alert.symbol))


def _sum_optional_by_currency(
    holdings: list[PortfolioHolding],
    field_name: str,
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for holding in holdings:
        amount = getattr(holding, field_name)
        if amount is None:
            continue
        totals.setdefault(holding.currency, Decimal("0"))
        totals[holding.currency] += amount
    return dict(sorted(totals.items()))


def _apply_rates(amounts_by_currency: dict[str, Decimal], rates: dict[str, Decimal]) -> Decimal:
    return sum(
        (amount * rates[currency] for currency, amount in amounts_by_currency.items()),
        Decimal("0"),
    )


def _safe_weight(value: Decimal, total: Decimal) -> Decimal:
    if total == 0:
        return Decimal("0")
    return value / total


def _stringify_amounts(amounts: dict[str, Decimal]) -> dict[str, str]:
    return {currency: str(amount) for currency, amount in amounts.items()}


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
