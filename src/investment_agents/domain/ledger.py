from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping

from investment_agents.domain.money import (
    DEFAULT_CURRENCY,
    decimal_or_zero,
    normalize_currency,
    optional_decimal,
)


HEADER_ALIASES = {
    "date": {"date", "trade date", "transaction date", "timestamp"},
    "symbol": {"symbol", "ticker", "asset", "instrument"},
    "side": {"side", "action", "type", "transaction type"},
    "quantity": {"quantity", "qty", "shares", "units"},
    "price": {"price", "unit price", "avg price", "average price"},
    "fees": {"fees", "fee", "commission", "costs"},
    "amount": {"amount", "total", "value", "net amount", "cash flow"},
    "currency": {"currency", "ccy"},
}

BUY_SIDES = {"buy", "bought", "purchase", "deposit"}
SELL_SIDES = {"sell", "sold", "sale", "withdrawal"}


@dataclass(frozen=True)
class LedgerTransaction:
    date: str | None
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal("0")
    amount: Decimal | None = None
    currency: str = DEFAULT_CURRENCY
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def signed_quantity(self) -> Decimal:
        side = self.side.lower()
        if side in SELL_SIDES:
            return -self.quantity
        return self.quantity

    @property
    def cash_flow(self) -> Decimal:
        if self.amount is not None:
            return self.amount
        gross = self.quantity * self.price
        if self.side.lower() in BUY_SIDES:
            return -(gross + self.fees)
        if self.side.lower() in SELL_SIDES:
            return gross - self.fees
        return gross - self.fees

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ["quantity", "price", "fees", "amount"]:
            if payload[key] is not None:
                payload[key] = str(payload[key])
        payload["signed_quantity"] = str(self.signed_quantity)
        payload["cash_flow"] = str(self.cash_flow)
        return payload


@dataclass(frozen=True)
class LedgerPosition:
    symbol: str
    currency: str
    quantity: Decimal
    net_cash_flow: Decimal
    transaction_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "currency": self.currency,
            "quantity": str(self.quantity),
            "net_cash_flow": str(self.net_cash_flow),
            "transaction_count": self.transaction_count,
        }


@dataclass(frozen=True)
class LedgerSummary:
    transaction_count: int
    symbols: list[str]
    currencies: list[str]
    total_fees: Decimal
    total_fees_by_currency: dict[str, Decimal]
    net_cash_flow_by_currency: dict[str, Decimal]
    positions: list[LedgerPosition]
    reporting_currency: str | None = None
    total_fees_reporting_currency: Decimal | None = None
    net_cash_flow_reporting_currency: Decimal | None = None
    fx_rates_used: dict[str, Decimal] = field(default_factory=dict)
    missing_fx_rates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_count": self.transaction_count,
            "symbols": self.symbols,
            "currencies": self.currencies,
            "total_fees": str(self.total_fees),
            "total_fees_by_currency": {
                currency: str(amount)
                for currency, amount in self.total_fees_by_currency.items()
            },
            "net_cash_flow_by_currency": {
                currency: str(amount)
                for currency, amount in self.net_cash_flow_by_currency.items()
            },
            "positions": [position.to_dict() for position in self.positions],
            "reporting_currency": self.reporting_currency,
            "total_fees_reporting_currency": (
                str(self.total_fees_reporting_currency)
                if self.total_fees_reporting_currency is not None
                else None
            ),
            "net_cash_flow_reporting_currency": (
                str(self.net_cash_flow_reporting_currency)
                if self.net_cash_flow_reporting_currency is not None
                else None
            ),
            "fx_rates_used": {
                currency: str(rate)
                for currency, rate in self.fx_rates_used.items()
            },
            "missing_fx_rates": self.missing_fx_rates,
            "warnings": self.warnings,
        }

    def to_summary_text(self) -> str:
        if self.transaction_count == 0:
            return "No ledger transactions were found."

        position_text = ", ".join(
            f"{position.symbol} {position.currency}: qty {position.quantity}, cash flow {position.net_cash_flow}"
            for position in self.positions
        )
        cash_flow_text = ", ".join(
            f"{currency} {amount}"
            for currency, amount in self.net_cash_flow_by_currency.items()
        )
        fees_text = ", ".join(
            f"{currency} {amount}"
            for currency, amount in self.total_fees_by_currency.items()
        )
        reporting_text = ""
        if self.reporting_currency and self.net_cash_flow_reporting_currency is not None:
            reporting_text = (
                f" Reporting-currency net cash flow: {self.reporting_currency} "
                f"{self.net_cash_flow_reporting_currency}; reporting-currency fees: "
                f"{self.reporting_currency} {self.total_fees_reporting_currency}."
            )
        elif self.reporting_currency and self.missing_fx_rates:
            reporting_text = (
                f" Reporting-currency totals need FX rates for: "
                f"{', '.join(self.missing_fx_rates)}."
            )

        return (
            f"Ledger contains {self.transaction_count} transactions across "
            f"{len(self.symbols)} symbols and {len(self.currencies)} currencies. "
            f"Net cash flow by currency: {cash_flow_text}; total fees by currency: {fees_text}. "
            f"Positions: {position_text}."
            f"{reporting_text}"
        )


def parse_ledger_rows(rows: list[list[Any]]) -> tuple[list[LedgerTransaction], list[str]]:
    if not rows:
        return [], ["Ledger sheet returned no rows."]

    header = [_normalize_header(value) for value in rows[0]]
    column_map = _build_column_map(header)
    warnings: list[str] = []

    required = ["symbol", "side", "quantity"]
    missing = [name for name in required if name not in column_map]
    if missing:
        return [], [f"Ledger sheet is missing required columns: {', '.join(missing)}."]

    transactions: list[LedgerTransaction] = []
    for index, row in enumerate(rows[1:], start=2):
        raw = _row_to_dict(header, row)
        symbol = _get_value(row, column_map, "symbol").upper()
        side = _get_value(row, column_map, "side").lower()
        quantity = decimal_or_zero(_get_value(row, column_map, "quantity"))
        price = decimal_or_zero(_get_value(row, column_map, "price"))
        fees = decimal_or_zero(_get_value(row, column_map, "fees"))
        amount = optional_decimal(_get_value(row, column_map, "amount"))
        currency = normalize_currency(_get_value(row, column_map, "currency"))
        traded_at = _parse_date(_get_value(row, column_map, "date"))

        if not symbol or not side or quantity == 0:
            warnings.append(f"Skipped row {index}: missing symbol, side, or quantity.")
            continue

        transactions.append(
            LedgerTransaction(
                date=traded_at,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                fees=fees,
                amount=amount,
                currency=currency,
                raw=raw,
            )
        )

    return transactions, warnings


def summarize_transactions(
    transactions: list[LedgerTransaction],
    warnings: list[str] | None = None,
    reporting_currency: str | None = None,
    fx_rates: Mapping[str, str | Decimal] | None = None,
) -> LedgerSummary:
    positions_by_symbol_currency: dict[tuple[str, str], dict[str, Any]] = {}
    for transaction in transactions:
        bucket = positions_by_symbol_currency.setdefault(
            (transaction.symbol, transaction.currency),
            {"quantity": Decimal("0"), "net_cash_flow": Decimal("0"), "count": 0},
        )
        bucket["quantity"] += transaction.signed_quantity
        bucket["net_cash_flow"] += transaction.cash_flow
        bucket["count"] += 1

    positions = [
        LedgerPosition(
            symbol=symbol,
            currency=currency,
            quantity=values["quantity"],
            net_cash_flow=values["net_cash_flow"],
            transaction_count=values["count"],
        )
        for (symbol, currency), values in sorted(positions_by_symbol_currency.items())
    ]
    total_fees_by_currency = _sum_by_currency(transactions, "fees")
    net_cash_flow_by_currency = _cash_flow_by_currency(transactions)
    normalized = _normalize_currency_totals(
        net_cash_flow_by_currency=net_cash_flow_by_currency,
        total_fees_by_currency=total_fees_by_currency,
        reporting_currency=reporting_currency,
        fx_rates=fx_rates or {},
    )

    return LedgerSummary(
        transaction_count=len(transactions),
        symbols=sorted({position.symbol for position in positions}),
        currencies=sorted({position.currency for position in positions}),
        total_fees=sum((transaction.fees for transaction in transactions), Decimal("0")),
        total_fees_by_currency=total_fees_by_currency,
        net_cash_flow_by_currency=net_cash_flow_by_currency,
        positions=positions,
        reporting_currency=normalized["reporting_currency"],
        total_fees_reporting_currency=normalized["total_fees_reporting_currency"],
        net_cash_flow_reporting_currency=normalized["net_cash_flow_reporting_currency"],
        fx_rates_used=normalized["fx_rates_used"],
        missing_fx_rates=normalized["missing_fx_rates"],
        warnings=warnings or [],
    )


def _normalize_currency_totals(
    net_cash_flow_by_currency: dict[str, Decimal],
    total_fees_by_currency: dict[str, Decimal],
    reporting_currency: str | None,
    fx_rates: Mapping[str, str | Decimal],
) -> dict[str, Any]:
    if not reporting_currency:
        return {
            "reporting_currency": None,
            "total_fees_reporting_currency": None,
            "net_cash_flow_reporting_currency": None,
            "fx_rates_used": {},
            "missing_fx_rates": [],
        }

    normalized_reporting_currency = normalize_currency(reporting_currency)
    currencies = sorted(set(net_cash_flow_by_currency) | set(total_fees_by_currency))
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
        return {
            "reporting_currency": normalized_reporting_currency,
            "total_fees_reporting_currency": None,
            "net_cash_flow_reporting_currency": None,
            "fx_rates_used": rates_used,
            "missing_fx_rates": missing_rates,
        }

    return {
        "reporting_currency": normalized_reporting_currency,
        "total_fees_reporting_currency": _apply_rates(total_fees_by_currency, rates_used),
        "net_cash_flow_reporting_currency": _apply_rates(net_cash_flow_by_currency, rates_used),
        "fx_rates_used": rates_used,
        "missing_fx_rates": [],
    }


def _apply_rates(amounts_by_currency: dict[str, Decimal], rates: dict[str, Decimal]) -> Decimal:
    return sum(
        (amount * rates[currency] for currency, amount in amounts_by_currency.items()),
        Decimal("0"),
    )


def _sum_by_currency(
    transactions: list[LedgerTransaction],
    field_name: str,
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for transaction in transactions:
        totals.setdefault(transaction.currency, Decimal("0"))
        totals[transaction.currency] += getattr(transaction, field_name)
    return dict(sorted(totals.items()))


def _cash_flow_by_currency(transactions: list[LedgerTransaction]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for transaction in transactions:
        totals.setdefault(transaction.currency, Decimal("0"))
        totals[transaction.currency] += transaction.cash_flow
    return dict(sorted(totals.items()))


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


def _normalize_header(value: Any) -> str:
    return str(value).strip().lower()


def _parse_date(value: str) -> str | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return value
