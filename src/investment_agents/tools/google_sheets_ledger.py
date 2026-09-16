from __future__ import annotations

from investment_agents.core.config import Settings
from investment_agents.domain.ledger import parse_ledger_rows, summarize_transactions
from investment_agents.domain.portfolio import parse_holding_rows, summarize_holdings
from investment_agents.domain.watchlist import parse_watchlist_rows, summarize_watchlist
from investment_agents.storage.market_cache import MarketDataCache
from investment_agents.tools.base import ToolReadiness, ToolResult

SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


class GoogleSheetsLedgerTool:
    """Future Google Sheets ledger adapter for P/L and portfolio interpretation."""

    name = "google_sheets_ledger"

    def __init__(self, settings: Settings, cache: MarketDataCache | None = None) -> None:
        self.settings = settings
        self.cache = cache

    def readiness(self) -> ToolReadiness:
        missing = []
        if not self.settings.google_ledger_sheet_id:
            missing.append("GOOGLE_LEDGER_SHEET_ID")
        if not self.settings.google_service_account_file:
            missing.append("GOOGLE_SERVICE_ACCOUNT_FILE")

        return ToolReadiness(
            tool_name=self.name,
            configured=not missing,
            status="ready" if not missing else "needs_configuration",
            missing_settings=missing,
            capabilities=[
                "ledger_transactions",
                "profit_loss_interpretation",
                "portfolio_allocation",
                "position_exposure",
                "holdings_snapshot",
                "watchlist_tracking",
                "concentration_risk",
                "threshold_alerts",
                "google_sheets_values_get",
                "fx_normalized_reporting",
            ],
        )

    def summarize_ledger(self, question: str) -> ToolResult:
        readiness = self.readiness()
        if not readiness.configured:
            return ToolResult(
                tool_name=self.name,
                status=readiness.status,
                summary=(
                    "Google ledger access is not configured yet. Missing settings: "
                    f"{', '.join(readiness.missing_settings)}."
                ),
                data={"question": question, "missing_settings": readiness.missing_settings},
            )

        rows = self.fetch_rows(self.settings.google_ledger_range)
        watchlist_rows = (
            self.fetch_rows(self.settings.google_watchlist_range)
            if self.settings.google_watchlist_range
            else []
        )
        transactions, ledger_warnings = parse_ledger_rows(rows)
        holdings, holdings_warnings = parse_holding_rows(rows)
        if self.settings.google_watchlist_range:
            watchlist_items, watchlist_warnings = parse_watchlist_rows(watchlist_rows)
        else:
            watchlist_items, watchlist_warnings = [], []
        fx_rates = {}
        if self.cache is not None:
            fx_rates = self.cache.latest_fx_rates(self.settings.reporting_currency)
        ledger_summary = summarize_transactions(
            transactions,
            ledger_warnings,
            reporting_currency=self.settings.reporting_currency,
            fx_rates=fx_rates,
        )
        portfolio_summary = summarize_holdings(
            holdings,
            holdings_warnings,
            reporting_currency=self.settings.reporting_currency,
            fx_rates=fx_rates,
            concentration_alert_threshold=self.settings.concentration_alert_threshold,
            loss_alert_threshold=self.settings.loss_alert_threshold,
        )
        watchlist_summary = summarize_watchlist(watchlist_items, watchlist_warnings)
        summary_texts = []
        if ledger_summary.transaction_count:
            summary_texts.append(ledger_summary.to_summary_text())
        if portfolio_summary.holding_count:
            summary_texts.append(portfolio_summary.to_summary_text())
        if watchlist_summary.item_count:
            summary_texts.append(watchlist_summary.to_summary_text())
        if not summary_texts:
            summary_texts = ledger_warnings + holdings_warnings + watchlist_warnings

        return ToolResult(
            tool_name=self.name,
            status=(
                "ok"
                if summary_texts and (
                    ledger_summary.transaction_count
                    or portfolio_summary.holding_count
                    or watchlist_summary.item_count
                )
                else "empty"
            ),
            summary=" ".join(summary_texts),
            data={
                "sheet_id": self.settings.google_ledger_sheet_id,
                "range": self.settings.google_ledger_range,
                "watchlist_range": self.settings.google_watchlist_range,
                "question": question,
                "ledger_summary": ledger_summary.to_dict(),
                "portfolio_summary": portfolio_summary.to_dict(),
                "watchlist_summary": watchlist_summary.to_dict(),
            },
        )

    def fetch_rows(self, range_name: str | None = None) -> list[list[str]]:
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Google Sheets dependencies are missing. Install "
                "google-api-python-client and google-auth."
            ) from exc

        credentials = service_account.Credentials.from_service_account_file(
            self.settings.google_service_account_file,
            scopes=[SHEETS_READONLY_SCOPE],
        )
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        response = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=self.settings.google_ledger_sheet_id,
                range=range_name or self.settings.google_ledger_range,
            )
            .execute()
        )
        return response.get("values", [])
