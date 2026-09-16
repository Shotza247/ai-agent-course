# Research System Prompt

The shared prompt lives in `src/investment_agents/core/messages.py` as
`DEFAULT_SYSTEM_PROMPT`. Reviewed on 2026-09-16; its exact text is:

> You are an expert market analysts who continously monitors daily market trends, and sentiments and cross checks them with 52-week highs, moving averages and other market related triggers and political and economic trends and shifts that will impact market volatility. Clearly state when the sources do not contain enough evidence.

This is the shared default for new conversations.
It describes the desired specialist role; it does not implement continuous
monitoring, price history retrieval, moving averages, or volatility analysis.

## Runtime Boundary

`FirstAgent` uses this default for new local Hugging Face chats. A caller can
explicitly supply a different system prompt or existing conversation. Restart the
local CLI and start a new conversation to use the updated default.

Streamlit also initializes history with `initial_chat()` and sends it with `/chat`.
Restart Streamlit and click **Clear conversation** to replace a previous session's
system message. That message is not displayed as a normal chat bubble.

The existing API orchestrator still builds template replies. Finnhub and Alpha
Vantage wrappers already fetch evidence for selected symbols, but do not call an
LLM. The shared prompt does not change their routing, tool calls, or API synthesis.
Connecting a model to their evidence is the next implementation step.

## Manual Checks

These are suggested evaluation cases, not verified behavior or guarantees made by
the shorter prompt. Supply evidence explicitly when testing local model chat;
that path does not automatically call the market or research adapters.

- Without tools: ask `What is AAPL trading at right now?` Expect an explicit
  inability to verify the current price, not an invented quote.
- Supply a clearly dated cached quote and ask for analysis. Expect its date and
  stale status to remain visible.
- Supply a provider rate-limit result. Expect a data gap, not neutral sentiment.
- Supply news and a same-day price decline. Expect possible explanations to be
  distinguished from demonstrated causes.

Prompt instructions are behavioral guidance, not a guarantee of model compliance.
These cases need real-model evaluation once evidence-based synthesis is connected.
