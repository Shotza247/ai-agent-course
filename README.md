# First Research Agent

A reusable research-agent prototype with a Streamlit chat interface, keyless web
search and scraping, and swappable local or hosted Hugging Face inference.

## Current Flow

```text
Streamlit UI
  -> LocalChatAgent
     -> LangGraph research workflow
        -> WebResearchTools (search, retrieve, extract)
        -> ResearchSynthesisSkill
        -> ChatModel adapter
           -> local Transformers pipeline
           or Hugging Face Inference Providers
```

The architecture is documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md),
and the folder responsibilities are mapped in
[`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md). FastAPI and MCP remain
planned boundaries; LangGraph now runs the research workflow.

The proposed financial multi-agent system and its implementation gates are in
[`docs/FINANCIAL_RESEARCH_BLUEPRINT.md`](docs/FINANCIAL_RESEARCH_BLUEPRINT.md).

## Setup

Create and activate a virtual environment:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

For local inference, install the appropriate PyTorch build first. For a CPU-only
machine:

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Then install the project dependencies:

```powershell
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and select one model backend.

## Model Backends

Local Transformers inference downloads and runs the model on this machine:

```dotenv
CHAT_MODEL_BACKEND=local
HF_MODEL_ID=HuggingFaceTB/SmolLM2-360M-Instruct
```

Hosted inference sends chat messages to Hugging Face Inference Providers:

```dotenv
CHAT_MODEL_BACKEND=huggingface
HF_TOKEN=hf_replace_with_your_token
HF_INFERENCE_MODEL_ID=Qwen/Qwen2.5-7B-Instruct-1M
HF_INFERENCE_PROVIDER=featherless-ai
HF_INFERENCE_TIMEOUT=60
```

`HF_TOKEN` is required for hosted inference and must never be committed. It is
optional in local mode unless the selected model is gated or private. Provider
and model availability can change, so verify both on the Hugging Face model page
when changing this configuration.

Restart Streamlit whenever `.env` changes because the running process retains
the environment and cached agent resources it started with.

## Run

Run the Streamlit research UI:

```powershell
python -m streamlit run apps/streamlit_app.py --server.port=8503 --server.fileWatcherType=none
```

Open `http://localhost:8503`, enter a question, and choose the number of sources.
The agent searches public webpages, synthesizes a concise answer, and places the
authoritative links inside a collapsed **Sources** section.

Run the terminal interface:

```powershell
py first_agent.py
```

## Verification

```powershell
python -m unittest discover -s tests -v
python -m compileall first_agent.py apps src tests
git diff --check
```

The current suite contains 16 tests covering model adapters, backend selection,
hosted request mapping, empty and unreachable provider responses, search-result
mapping, DNS recovery, HTML extraction, public-URL enforcement, agent-tool
integration, chat history, citation cleanup, workflow routing, checkpointed
short-term state, and namespaced long-term memory.

Live search and hosted inference are smoke-tested separately because public
services, account credits, and provider availability are not deterministic.

## Project Structure

- `apps/`: Streamlit and future interface entry points.
- `src/first_agent/agents/`: public agent facades.
- `src/first_agent/workflows/`: LangGraph state, nodes, and routing.
- `src/first_agent/memory/`: short-term checkpoints and long-term memory stores.
- `src/first_agent/skills/`: reusable research behaviors and response rules.
- `src/first_agent/prompts/`: prompt construction.
- `src/first_agent/config/`: code-level defaults.
- `src/first_agent/models/`: neutral model contract, factory, and adapters.
- `src/first_agent/tools/`: web search and scraping tools.
- `src/first_agent/agent.py`: backward-compatible public import path.
- `tests/`: deterministic unit and integration-boundary tests.
- `docs/`: architecture and operating guides.
- `logs/`: runtime, crash, replay, and test logs; no `.log` files belong in the project root.
- `assets/`: future images, documents, and static assets.
- `skills/`: future distributable skill definitions and instructions.
- `mcp/`: future MCP server configuration and setup.
- `tools/`: future standalone tool adapters and helper scripts.
- `audit_log.md`: chronological implementation and incident trail.

## Reliability Notes

- Search uses DDGS without an API key, direct HTTP retrieval, and Jina Reader as
  a fallback. Public services may rate-limit or temporarily fail.
- The scraper permits only public HTTP(S) targets and validates redirects to
  reduce server-side request forgery risk.
- Search DNS failures return a recoverable no-sources response. Hosted provider
  DNS, timeout, and HTTP failures return a concise retry message.
- The local model is useful for lightweight development but generally produces
  weaker research summaries than the configured hosted model.

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for startup, troubleshooting, log,
and Hugging Face usage-monitoring procedures.
