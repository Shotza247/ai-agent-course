from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RawPayloadRecord:
    source: str
    endpoint: str
    cache_key: str
    payload: dict[str, Any]
    fetched_at: str


@dataclass(frozen=True)
class FxRateRecord:
    base_currency: str
    quote_currency: str
    rate: Decimal
    observed_at: str
    source: str

    def to_dict(self) -> dict[str, str]:
        return {
            "base_currency": self.base_currency,
            "quote_currency": self.quote_currency,
            "rate": str(self.rate),
            "observed_at": self.observed_at,
            "source": self.source,
        }


class MarketDataCache:
    """DuckDB-backed cache for raw API payloads, curated snapshots, and FX rates."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._connection = None

    def get_fresh_raw_payload(
        self,
        source: str,
        endpoint: str,
        cache_key: str,
        ttl_seconds: int,
    ) -> RawPayloadRecord | None:
        row = self._connect().execute(
            """
            select source, endpoint, cache_key, payload_json, fetched_at
            from raw_api_payloads
            where source = ? and endpoint = ? and cache_key = ?
            order by fetched_at desc
            limit 1
            """,
            [source, endpoint, cache_key],
        ).fetchone()
        if not row:
            return None

        fetched_at = _parse_datetime(row[4])
        if (datetime.now(timezone.utc) - fetched_at).total_seconds() > ttl_seconds:
            return None

        return _raw_payload_from_row(row, fetched_at)

    def get_latest_raw_payload(
        self,
        source: str,
        endpoint: str,
        cache_key: str,
    ) -> RawPayloadRecord | None:
        row = self._connect().execute(
            """
            select source, endpoint, cache_key, payload_json, fetched_at
            from raw_api_payloads
            where source = ? and endpoint = ? and cache_key = ?
            order by fetched_at desc
            limit 1
            """,
            [source, endpoint, cache_key],
        ).fetchone()
        if not row:
            return None

        return _raw_payload_from_row(row, _parse_datetime(row[4]))

    def store_raw_payload(
        self,
        source: str,
        endpoint: str,
        cache_key: str,
        payload: dict[str, Any],
        fetched_at: str | None = None,
    ) -> RawPayloadRecord:
        fetched_at = fetched_at or utc_now_iso()
        self._connect().execute(
            """
            insert into raw_api_payloads
            (source, endpoint, cache_key, payload_json, fetched_at)
            values (?, ?, ?, ?, ?)
            """,
            [source, endpoint, cache_key, json.dumps(payload), fetched_at],
        )
        return RawPayloadRecord(
            source=source,
            endpoint=endpoint,
            cache_key=cache_key,
            payload=payload,
            fetched_at=fetched_at,
        )

    def store_curated_snapshot(
        self,
        source: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
    ) -> None:
        self._connect().execute(
            """
            insert into curated_snapshots
            (source, entity_type, entity_id, payload_json, observed_at)
            values (?, ?, ?, ?, ?)
            """,
            [source, entity_type, entity_id, json.dumps(payload), utc_now_iso()],
        )

    def store_fx_rate(
        self,
        base_currency: str,
        quote_currency: str,
        rate: str | Decimal,
        source: str = "manual",
        observed_at: str | None = None,
    ) -> FxRateRecord:
        normalized_base = base_currency.strip().upper()
        normalized_quote = quote_currency.strip().upper()
        parsed_rate = Decimal(str(rate))
        observed = observed_at or utc_now_iso()

        self._connect().execute(
            """
            insert into fx_rates
            (base_currency, quote_currency, rate, source, observed_at)
            values (?, ?, ?, ?, ?)
            """,
            [normalized_base, normalized_quote, str(parsed_rate), source, observed],
        )
        return FxRateRecord(
            base_currency=normalized_base,
            quote_currency=normalized_quote,
            rate=parsed_rate,
            observed_at=observed,
            source=source,
        )

    def latest_fx_rates(self, quote_currency: str) -> dict[str, Decimal]:
        normalized_quote = quote_currency.strip().upper()
        rows = self._connect().execute(
            """
            select base_currency, rate, observed_at
            from fx_rates
            where quote_currency = ?
            order by observed_at desc
            """,
            [normalized_quote],
        ).fetchall()

        latest: dict[str, Decimal] = {}
        for base_currency, rate, _observed_at in rows:
            if base_currency not in latest:
                latest[base_currency] = Decimal(str(rate))
        latest[normalized_quote] = Decimal("1")
        return dict(sorted(latest.items()))

    def status(self) -> dict[str, Any]:
        exists = self.db_path.exists()
        status = {
            "db_path": str(self.db_path),
            "exists": exists,
        }
        if exists:
            connection = self._connect()
            status["raw_payload_count"] = connection.execute(
                "select count(*) from raw_api_payloads"
            ).fetchone()[0]
            status["curated_snapshot_count"] = connection.execute(
                "select count(*) from curated_snapshots"
            ).fetchone()[0]
            status["fx_rate_count"] = connection.execute(
                "select count(*) from fx_rates"
            ).fetchone()[0]
        return status

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _connect(self):
        if self._connection is None:
            try:
                import duckdb
            except ImportError as exc:
                raise RuntimeError("DuckDB is not installed. Install the duckdb package.") from exc

            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = duckdb.connect(str(self.db_path))
            self._initialize_schema()
        return self._connection

    def _initialize_schema(self) -> None:
        self._connection.execute(
            """
            create table if not exists raw_api_payloads (
                source varchar not null,
                endpoint varchar not null,
                cache_key varchar not null,
                payload_json varchar not null,
                fetched_at varchar not null
            )
            """
        )
        self._connection.execute(
            """
            create table if not exists curated_snapshots (
                source varchar not null,
                entity_type varchar not null,
                entity_id varchar not null,
                payload_json varchar not null,
                observed_at varchar not null
            )
            """
        )
        self._connection.execute(
            """
            create table if not exists fx_rates (
                base_currency varchar not null,
                quote_currency varchar not null,
                rate varchar not null,
                source varchar not null,
                observed_at varchar not null
            )
            """
        )


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _raw_payload_from_row(row: Any, fetched_at: datetime) -> RawPayloadRecord:
    return RawPayloadRecord(
        source=row[0],
        endpoint=row[1],
        cache_key=row[2],
        payload=json.loads(row[3]),
        fetched_at=fetched_at.isoformat(),
    )
