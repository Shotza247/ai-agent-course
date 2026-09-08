# Financial Research Agent Blueprint

## Purpose

Evolve the current research agent into a reusable, evidence-grounded financial
research system using Finnhub, Alpha Vantage, Hugging Face chat models, and
LangGraph orchestration.

The system is for research and decision support, not autonomous trading or
personalized financial advice. Every output must identify its data timestamp,
provider, important uncertainty, and material limitations.

## Design Principles

1. Use deterministic code for data retrieval, normalization, calculations,
   validation, caching, and routing whenever possible.
2. Use LLM agents for planning, interpretation, comparison, and synthesis.
3. Keep provider-specific JSON outside graph state and application interfaces.
4. Preserve evidence lineage from API response to final claim.
5. Prefer a controlled graph with bounded parallelism over an open-ended agent
   swarm.
6. Treat price freshness, currencies, market sessions, corporate actions, and
   delayed data as first-class fields.
7. Make partial results explicit when a provider is unavailable or rate-limited.

## Target Architecture

```text
Streamlit or another client
  -> FastAPI
     -> FinancialResearchGraph (LangGraph)
        -> request and symbol resolver
        -> research planner
        -> market-data gateway
           -> Finnhub adapter
           -> Alpha Vantage adapter
           -> cache + rate limiter
        -> fundamentals analyst
        -> market and technical analyst
        -> news and catalyst analyst
        -> risk analyst
        -> evidence validator
        -> synthesis agent
     -> brief and run repository

Market-data gateway
  -> Python tool interface initially
  -> streamable HTTP MCP server when the contracts are stable
```

## Why This Is Multi-Agent

The specialists have different prompts, context, evidence, and output schemas,
but they do not call each other directly. A parent LangGraph owns routing and
shared state. Specialist subgraphs should be per-invocation by default so their
private context does not accumulate between unrelated research runs.

Start with one hosted Hugging Face model profile for every LLM node. Add separate
planner, analyst, and synthesis model profiles only after evaluations show a
quality, latency, or cost benefit.

## Graph Design

```text
START
  -> validate_request
  -> resolve_instrument
  -> plan_research
  -> [fetch_quote, fetch_prices, fetch_fundamentals, fetch_news]
  -> normalize_and_validate
  -> compute_metrics
  -> [fundamentals_agent, market_agent, catalyst_agent, risk_agent]
  -> validate_evidence
  -> synthesize_brief
  -> quality_gate
  -> persist_run_and_brief
  -> END
```

Fetch and specialist nodes can fan out in parallel, subject to provider-specific
concurrency and quota controls. The graph should continue with partial evidence
when non-essential branches fail and stop when identity, timestamps, or minimum
evidence requirements cannot be established.

### Node Responsibilities

| Node | Type | Responsibility |
| --- | --- | --- |
| `validate_request` | deterministic | Validate ticker/query, horizon, market, currency, and requested sections. |
| `resolve_instrument` | deterministic tool | Resolve ticker ambiguity and exchange identity before fetching data. |
| `plan_research` | LLM with structured output | Select required research sections and data needs from an allowlist. |
| `fetch_*` | deterministic tools | Call normalized gateway methods with retries, caching, and rate limits. |
| `normalize_and_validate` | deterministic | Convert provider payloads, reject malformed values, and attach lineage. |
| `compute_metrics` | deterministic | Calculate returns, volatility, drawdown, trend, valuation ratios, and comparisons. |
| specialist agents | LLM with structured output | Interpret only the evidence assigned to each specialty. |
| `validate_evidence` | deterministic plus optional LLM | Reject unsupported claims, stale facts, missing citations, and unit mismatches. |
| `synthesize_brief` | LLM with structured output | Merge validated findings into a concise financial research brief. |
| `quality_gate` | deterministic | Enforce schema, coverage, freshness, disclaimers, and source references. |
| `persist_run_and_brief` | deterministic | Save run metadata, evidence references, findings, and final brief version. |

## Specialist Agents

### Research Planner

- Interprets the question and requested horizon.
- Produces a bounded `ResearchPlan`; it cannot invent tool names or endpoints.
- Identifies comparison tickers and required sections.

### Fundamentals Analyst

- Reviews company profile, financial statements, earnings, valuation, and growth.
- Distinguishes reported values from calculated metrics.
- Flags missing periods, inconsistent currencies, and one-time items.

### Market and Technical Analyst

- Uses canonical OHLCV series and deterministic indicators.
- Describes trend, momentum, volatility, liquidity, and drawdown.
- Never asks an LLM to calculate indicators from raw text.

### News and Catalyst Analyst

- Groups duplicate stories and separates company events from market-wide news.
- Identifies catalysts, dates, sentiment evidence, and conflicting coverage.
- Does not treat provider sentiment scores as facts about future returns.

### Risk Analyst

- Builds a categorized risk register: market, financial, operational,
  regulatory, concentration, event, data-quality, and model risk.
- Connects every risk or counterpoint to evidence.

### Synthesis Agent

- Receives structured specialist findings, not full provider payloads.
- Produces a balanced brief with snapshot, thesis, evidence, catalysts, risks,
  uncertainties, and source references.
- Must not issue personalized buy/sell instructions.

## Canonical Data Contracts

Use Pydantic models at every external boundary. Keep graph state JSON-serializable
and store large tables or raw payloads by reference rather than embedding Pandas
objects in checkpoints.

Core models:

- `Instrument`: symbol, exchange, security type, name, currency, identifiers.
- `QuoteSnapshot`: price, change, volume, market status, event time, retrieved time.
- `OHLCVBar`: adjusted/unadjusted prices, volume, interval, timezone, source.
- `FundamentalSnapshot`: metric, value, unit, currency, period, filing date.
- `NewsItem`: headline, summary, publisher, URL, published time, related symbols.
- `IndicatorValue`: name, parameters, value, observation time, input-series version.
- `EvidenceRecord`: provider, endpoint, request hash, retrieved time, event time,
  freshness class, raw reference, normalized reference, and validation status.
- `AgentFinding`: claim, explanation, evidence IDs, confidence, limitations.
- `ResearchBrief`: ticker, as-of time, sections, findings, risks, catalysts, sources,
  quality status, and version.

Every monetary field must carry currency. Every market fact must distinguish the
event timestamp from retrieval time. Every time series must state interval,
timezone, adjustment policy, and sort order.

## Market-Data Gateway

Create one internal interface instead of exposing provider endpoints directly to
agents:

```text
resolve_symbol(query, exchange?)
get_quote(instrument)
get_price_history(instrument, interval, start, end, adjusted)
get_company_profile(instrument)
get_fundamentals(instrument, periods, metrics)
get_company_news(instrument, start, end)
get_market_news(category, start, end)
get_earnings_calendar(instrument?, start, end)
```

Provider routing should be policy-driven:

- Choose a primary provider per canonical operation.
- Use the second provider only as a documented fallback or validation source.
- Never silently merge conflicting values.
- Return provenance and a warning when fallback data is used.
- Cache by provider, endpoint, normalized parameters, and data-adjustment policy.

Finnhub authenticates with `X-Finnhub-Token` or a token query parameter and
returns HTTP 429 when limits are exceeded. Alpha Vantage uses an API key and its
free service currently documents 25 requests per day. Therefore, quota-aware
caching and request coalescing are required before multi-agent fan-out.

Recommended cache policy:

| Data | Example TTL |
| --- | --- |
| quote or market status | 15-60 seconds while market is open |
| intraday bars | 1-5 minutes |
| daily bars | until the next expected market update |
| fundamentals | 6-24 hours, invalidated after new filing/earnings |
| company profile | 7 days |
| news | 5-15 minutes |

TTL values are policy defaults, not guarantees of exchange-level real-time data.

## Persistence and Saved Briefs

Use PostgreSQL in production and SQLite only for local prototyping. Suggested
tables:

- `research_runs`: request, status, graph version, model profile, timestamps,
  token/cost metadata, and error summary.
- `evidence_records`: normalized provenance and pointers to raw payloads.
- `agent_findings`: specialist, structured finding, confidence, evidence IDs.
- `research_briefs`: ticker, as-of time, rendered and structured brief, version.
- `brief_refreshes`: previous brief, new brief, material changes, refresh reason.
- `watchlists`: user/project, ticker, refresh policy, last successful refresh.

Saved ticker briefs should be immutable versions. A refresh creates a new version
and a change summary rather than overwriting prior research.

## LangChain and Hugging Face Model Layer

Introduce a LangChain-compatible model factory while preserving the existing
provider configuration. Graph nodes should depend on a model profile, not a
specific Hugging Face model ID:

```text
planner -> financial_planner profile
specialists -> financial_analyst profile
synthesis -> financial_synthesizer profile
```

Each profile defines provider, model, temperature, output limit, timeout, and
structured-output strategy. Hugging Face tool calling is provider/model
dependent, so the first graph should route tools deterministically and use LLMs
for schema-constrained decisions. Native tool calling can be evaluated later.

## FastAPI Contract

Keep the existing planned endpoints and add explicit research resources:

```text
GET  /health
POST /chat
POST /agents/{agent_id}/chat
POST /research/runs
GET  /research/runs/{run_id}
GET  /research/runs/{run_id}/events
GET  /briefs/{ticker}
POST /briefs/{ticker}/refresh
GET  /briefs/{ticker}/history
```

`POST /agents/financial-research/chat` can remain the conversational entry point.
Long-running refreshes should return a run ID and expose progress through server-
sent events or a polling endpoint. API responses should return `answer`,
`sources`, `as_of`, `warnings`, and `run_id` as separate fields.

## MCP Direction

After the gateway contracts and fixtures are stable, expose the canonical tools
from one `market-data-mcp` server over streamable HTTP. Keep Finnhub and Alpha
Vantage keys on the server. The MCP server should enforce input schemas, quotas,
timeouts, cache policy, provenance, and response-size limits.

Do not expose arbitrary provider URLs, raw HTTP fetches, or unrestricted function
names to the model.

## Evaluation and Quality Gates

Create a fixed evaluation set across:

- common US equities, non-US listings, ETFs, and ambiguous symbols;
- market-open and market-closed questions;
- current snapshot, historical comparison, earnings, news, and risk requests;
- missing data, quota exhaustion, stale data, provider disagreement, and timeout;
- prompt injection inside news text or scraped pages.

Measure:

- citation precision and claim support;
- numeric correctness against normalized fixtures;
- freshness and timestamp correctness;
- section completeness and uncertainty disclosure;
- provider calls, cache-hit rate, latency, tokens, and estimated cost;
- successful partial-result behavior under injected failures.

A release fails if unsupported numeric claims reach the brief, evidence IDs are
missing, currencies or periods are ambiguous, or the system hides stale/fallback
data.

## Implementation Plan

### Phase 0: Contracts and Fixtures

- Define canonical Pydantic models and `FinancialResearchState`.
- Capture sanitized Finnhub and Alpha Vantage fixtures for each selected endpoint.
- Define freshness, fallback, and minimum-evidence policies.
- Add contract and normalization tests.

Exit gate: provider fixtures normalize into identical canonical types without an
LLM or network call.

### Phase 1: Provider Clients and Gateway

- Implement typed Finnhub and Alpha Vantage clients with secret-safe headers.
- Add timeout, retry, 429 handling, quota budgets, caching, and request coalescing.
- Implement explicit provider-routing and conflict policies.
- Add mocked tests and opt-in live smoke tests.

Exit gate: every gateway operation has deterministic tests, provenance, and
documented degradation behavior.

### Phase 2: Deterministic LangGraph Skeleton

- Add `langgraph` explicitly to dependencies.
- Implement graph state, routing, parallel fetch nodes, and partial-failure paths.
- Use fake model and gateway implementations in graph tests.
- Add an in-memory checkpointer for development.

Exit gate: the graph completes, resumes, and degrades correctly without external
services.

### Phase 3: Specialist Agents

- Add structured planner and specialist output schemas.
- Wrap the Hugging Face model behind LangChain-compatible model profiles.
- Implement fundamentals, market, catalyst, risk, evidence, and synthesis nodes.
- Evaluate one shared model before assigning different models per role.

Exit gate: evaluation fixtures produce supported findings with evidence IDs and
no unverified calculations.

### Phase 4: Persistence and Refresh History

- Add repositories for runs, evidence, findings, briefs, and refresh history.
- Use immutable brief versions and material-change summaries.
- Add checkpoint persistence and stable thread/run identifiers.

Exit gate: interrupted runs resume safely and prior briefs remain reproducible.

### Phase 5: FastAPI

- Add `/health`, `/chat`, `/agents/{agent_id}/chat`, run, and brief endpoints.
- Separate synchronous chat from long-running research jobs.
- Add auth, request limits, structured errors, and event streaming or polling.

Exit gate: API contract tests pass independently of Streamlit.

### Phase 6: Streamlit Client Migration

- Replace direct agent calls with the FastAPI client.
- Preserve chat history and the collapsed Sources UI.
- Add research progress, as-of time, warnings, and saved-brief/history views.

Exit gate: existing UI behavior remains intact and all new fields render without
duplicated citations.

### Phase 7: Streamable HTTP MCP

- Expose stable gateway operations as MCP tools.
- Connect the graph through an MCP client adapter.
- Add tool schema, authentication, timeout, quota, and injection-resistance tests.

Exit gate: the graph can switch between in-process and MCP tool transports using
the same canonical contracts.

## Initial Scope Recommendation

The first useful financial brief should support one equity ticker and include:

- instrument identity and delayed/current quote context;
- one year of daily prices;
- company profile and a small, defined fundamentals set;
- recent company news and upcoming/recent earnings context;
- deterministic return, volatility, drawdown, and trend metrics;
- concise fundamentals, market, catalyst, and risk findings;
- evidence-linked synthesis with timestamps and limitations.

Defer forex, crypto, options, real-time streaming, portfolio advice, autonomous
alerts, and broad peer discovery until this vertical slice passes evaluation.

## Decisions Required Before Implementation

1. Confirm the first supported asset scope: US equities only is recommended.
2. Confirm which Finnhub and Alpha Vantage plans/quotas are available.
3. Select the initial canonical endpoints and provider priority for each.
4. Choose local SQLite versus PostgreSQL for the first persistence milestone.
5. Define whether briefs are educational research only or support regulated users.
6. Define acceptable latency, daily API-call budget, and hosted-model budget.

## Official References

- Finnhub API documentation: https://finnhub.io/docs/api
- Alpha Vantage API documentation: https://www.alphavantage.co/documentation/
- Alpha Vantage support and free limits: https://www.alphavantage.co/support/
- LangGraph graph API: https://docs.langchain.com/oss/python/langgraph/graph-api
- LangGraph persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph subgraphs: https://docs.langchain.com/oss/python/langgraph/use-subgraphs
- LangChain subagents: https://docs.langchain.com/oss/python/langchain/multi-agent/subagents
- Hugging Face function calling: https://huggingface.co/docs/inference-providers/guides/function-calling
