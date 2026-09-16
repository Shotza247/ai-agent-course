# Architecture

## Objective

Build reusable agent infrastructure in independently testable phases while
keeping presentation, orchestration, tools, and model providers replaceable.

The target flow is:

```text
Streamlit or another client
  -> FastAPI /chat or /agents/{agent_id}/chat
     -> LangGraph agent workflow
        -> chat-model adapter
        -> HTTP tool adapters or streamable HTTP MCP servers
```

## Implemented Components

### Interface

`apps/streamlit_app.py` owns chat rendering and user controls. It calls
`LocalChatAgent` directly today. Source links are separated from answer text by
the `**Sources**` marker and rendered in a collapsed expander.

### Agent

`src/first_agent/agents/research_agent.py` is the public facade. It composes the
model, tools, skill, memory, and workflow while preserving the existing
`LocalChatAgent` interface. `src/first_agent/agent.py` remains a compatibility
import for existing callers.

### Workflow

`src/first_agent/workflows/research.py` owns the deterministic LangGraph sequence:

1. Accept the user question and chat history.
2. Ask `WebResearchTools` for public sources.
3. Route no-source requests to a stable recovery answer.
4. Build an evidence-only synthesis prompt through the research skill.
5. Ask the configured `ChatModel` for a summary.
6. Remove model-generated citation sections and append authoritative links.

The compiled graph uses an in-memory checkpointer. Each run can receive a
`thread_id`, allowing callers to inspect thread-scoped workflow state during
local development.

### Memory

`src/first_agent/memory/short_term.py` provides LangGraph checkpoint memory.
It is process-local and is not suitable for durable deployment storage.

`src/first_agent/memory/long_term.py` provides a small namespaced in-memory
contract for explicit saved preferences or research metadata. It is tested but
is not automatically populated by the agent. A durable database-backed store,
retention rules, and user consent should precede production use.

### Model Boundary

`ChatModel` is a provider-neutral protocol with one `generate()` operation.
`create_chat_model()` selects an implementation from `CHAT_MODEL_BACKEND`:

- `TransformersChatModel`: cached local Hugging Face pipeline.
- `HuggingFaceInferenceChatModel`: hosted `InferenceClient.chat_completion()`.

The agent depends on the protocol, not either provider implementation. This
allows future LangChain chat models to be wrapped or adapted without changing
the agent contract.

### Tool Boundary

`WebResearchTools` provides search, public URL validation, retrieval, redirect
checks, HTML extraction, and Jina Reader fallback. It is currently an in-process
Python dependency. Its return values are structured `ResearchSource` objects.

## Security and Failure Boundaries

- `.env` and `.streamlit/secrets.toml` are ignored by Git.
- Hosted mode requires `HF_TOKEN`; source code and logs must never contain it.
- Scraping rejects non-HTTP schemes, URL credentials, private addresses, and
  redirects to non-public destinations.
- Responses are limited to 2 MB and extracted content is limited per source.
- Search transport failures degrade to no sources instead of exposing sockets.
- Hosted inference converts HTTP, timeout, and DNS failures to a stable message.

## Migration Status

- Complete: extract a provider-neutral model adapter.
- Complete: connect the adapter to Hugging Face Inference Providers.
- Complete: preserve Streamlit chat and Sources behavior.
- Complete: introduce LangGraph around research, tool, and synthesis nodes.
- Complete: add development short-term checkpoints and a namespaced long-term
  memory contract without silently storing user content.
- Planned: expose the completed workflow through FastAPI `/health`, `/chat`, and
  `/agents/{agent_id}/chat` endpoints.
- Planned: replace or supplement in-process tools with streamable HTTP MCP
  servers or explicit HTTP tool adapters.

FastAPI should own transport concerns and dependency creation. LangGraph should
own workflow state and routing. Model adapters should own provider SDK details.
MCP or HTTP adapters should own remote tool transport. Streamlit should remain a
client and must not contain orchestration logic.

## API Contract Direction

The future API should use stable request and response schemas independent of
Streamlit and any model provider. A response should keep answer text and sources
as separate structured fields rather than relying on the current Markdown
separator. The Streamlit client can then render the same collapsed Sources UI
from structured data.

## Financial Research Extension

The approved direction for the next domain-specific evolution is documented in
[`FINANCIAL_RESEARCH_BLUEPRINT.md`](FINANCIAL_RESEARCH_BLUEPRINT.md). It defines
the controlled multi-agent graph, normalized Finnhub and Alpha Vantage gateway,
financial evidence contracts, saved briefs, refresh history, quality gates, and
the staged path to FastAPI and streamable HTTP MCP.
