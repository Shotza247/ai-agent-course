# First Research Agent

A reusable research-agent prototype built in Python for exploring public web content, synthesizing findings, and returning an answer with source links. It combines a Streamlit interface, a LangGraph workflow, web search/scraping tools, and a provider-neutral chat model layer.

## What this project does

The agent can:

- accept a user question in a chat interface
- search for public web sources using DuckDuckGo (without an API key)
- retrieve and extract page content
- validate that URLs are public and safe to access
- build an evidence-backed prompt from the retrieved sources
- generate a concise answer using a local or hosted model
- attach authoritative source links in a collapsed `Sources` section

This is designed as a practical learning project and an extensible foundation for more advanced multi-agent research systems.

## Current flow

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

The architecture is documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and the repository layout is described in [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md).

## Key features

- Research workflow orchestration with LangGraph
- Provider-neutral model abstraction for local and hosted inference
- Reusable synthesis and formatting logic via `ResearchSynthesisSkill`
- Web search and retrieval using public HTTP endpoints
- Safe URL validation and redirect handling
- Short-term workflow checkpoints and a namespaced long-term memory contract
- Unit tests covering adapters, workflow behavior, tool integration, and resilience paths

## Project goals

This repo is intended to demonstrate how to build a research-oriented agent with clear boundaries between:

- user interface (`apps/`)
- orchestration (`src/first_agent/workflows/`)
- model adapters (`src/first_agent/models/`)
- tool implementations (`src/first_agent/tools/`)
- prompt and synthesis logic (`src/first_agent/skills/`, `src/first_agent/prompts/`)
- memory (`src/first_agent/memory/`)

The long-term direction includes FastAPI transport and future MCP-style tool boundaries, as described in the docs.

## Setup

Create and activate a virtual environment:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

For local inference, install the appropriate PyTorch build first. For a CPU-only machine:

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Then install the project dependencies:

```powershell
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set the model backend you want to use.

## Model backends

### Local Transformers inference

This runs the model on the local machine:

```dotenv
CHAT_MODEL_BACKEND=local
HF_MODEL_ID=HuggingFaceTB/SmolLM2-360M-Instruct
```

### Hosted Hugging Face inference

This sends requests through Hugging Face Inference Providers:

```dotenv
CHAT_MODEL_BACKEND=huggingface
HF_TOKEN=hf_replace_with_your_token
HF_INFERENCE_MODEL_ID=Qwen/Qwen2.5-7B-Instruct-1M
HF_INFERENCE_PROVIDER=featherless-ai
HF_INFERENCE_TIMEOUT=60
```

`HF_TOKEN` is required for hosted inference and must never be committed. It is optional in local mode unless the selected model is gated or private. Provider and model availability can change, so verify both on the Hugging Face model page before switching configuration.

Note: restart Streamlit whenever `.env` changes because the process keeps the environment and cached agent resources it started with.

## Run the app

Run the Streamlit research UI:

```powershell
python -m streamlit run apps/streamlit_app.py --server.port=8503 --server.fileWatcherType=none
```

Open `http://localhost:8503`, enter a question, and choose the number of sources. The agent searches public webpages, synthesizes a concise answer, and places the authoritative links inside a collapsed **Sources** section.

## Run the terminal interface

```powershell
py first_agent.py
```

## Verification

```powershell
python -m unittest discover -s tests -v
python -m compileall first_agent.py apps src tests
git diff --check
```

The current test suite covers:

- model adapters
- backend selection
- hosted request mapping
- empty and unreachable provider responses
- search-result mapping
- DNS recovery
- HTML extraction
- public-URL enforcement
- agent-tool integration
- chat history
- citation cleanup
- workflow routing
- checkpointed short-term state
- namespaced long-term memory

Live search and hosted inference are smoke-tested separately because public services, account credits, and provider availability are not deterministic.

## Project structure

```text
ai-agent-course/
├── apps/                         # Streamlit and future interface entry points
├── src/first_agent/
│   ├── agents/                   # Public agent facades
│   ├── workflows/                # LangGraph state, nodes, routing, and edges
│   ├── memory/                   # Short-term checkpoints and long-term memory stores
│   ├── skills/                   # Reusable research behaviors and synthesis rules
│   ├── prompts/                  # Prompt construction
│   ├── config/                   # Code-level defaults
│   ├── models/                   # Model contract, factory, and adapters
│   ├── tools/                    # Web search and scraping tools
│   ├── agent.py                  # Compatibility import path
│   └── __init__.py
├── tests/                        # Deterministic unit and integration-boundary tests
├── docs/                         # Architecture and operations docs
├── logs/                         # Runtime, crash, replay, and test logs
├── assets/                       # Future images, docs, and static assets
├── skills/                       # Future distributable skill definitions
├── mcp/                          # Future MCP server config and setup
├── tools/                        # Future standalone tool adapters and scripts
├── first_agent.py                # CLI entry point
├── requirements.txt
├── .env.example
├── README.md
├── audit_log.md                  # Chronological implementation and incident trail
└── ...
```

## Reliability notes

- Search uses DDGS without an API key, direct HTTP retrieval, and Jina Reader as a fallback.
- The scraper allows only public HTTP(S) targets and validates redirects to reduce SSRF risk.
- Search DNS failures degrade to a recoverable no-sources response.
- Hosted provider DNS, timeout, and HTTP failures return a concise retry message.
- The local model is useful for lightweight development but generally produces weaker research summaries than a hosted model.

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for startup, troubleshooting, log, and Hugging Face usage-monitoring procedures.

## Repository status

This project is a working prototype with a clear separation of concerns and a documented architecture. It is primarily intended for learning, experimentation, and further extension into a more formal research or multi-agent system.
