from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


DEFAULT_CURRENCY = "UNKNOWN"


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = DEFAULT_CURRENCY

    def to_dict(self) -> dict[str, str]:
        return {"amount": str(self.amount), "currency": self.currency}


def normalize_currency(value: str | None) -> str:
    if not value:
        return DEFAULT_CURRENCY
    return value.strip().upper()


def decimal_or_zero(value: str) -> Decimal:
    parsed = optional_decimal(value)
    return parsed if parsed is not None else Decimal("0")


def optional_decimal(value: str) -> Decimal | None:
    if not value:
        return None
    cleaned = value.replace(",", "").replace("$", "").replace("R", "").strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None
