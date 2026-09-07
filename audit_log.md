# Audit Log

## 2026-09-07 20:15 - DNS Failure in Research UI

- Status: fixed
- Symptom: Streamlit displayed `Agent error: [Errno 11001] getaddrinfo failed` after submitting a research request.
- Scope: running Streamlit process, DDGS search boundary, and hosted Hugging Face adapter.
- Suspected cause: transient hostname resolution failure escaped from the search call before per-page recovery; the running UI also predated the hosted-backend `.env` update.
- Evidence:
  - DNS checks subsequently resolved `duckduckgo.com`, `router.huggingface.co`, and `r.jina.ai` successfully, indicating a transient rather than persistent resolver failure.
  - The old port-8503 log showed local Transformers weights loading, proving the process had not read the new hosted configuration.
- Changes:
  - Restarted Streamlit on port 8503; the fresh server returned HTTP 200.
  - `WebResearchTools.research()` now converts DDGS, HTTP, and OS-level search failures into an empty-source result handled by the agent's existing retry response.
  - `HuggingFaceInferenceChatModel` now translates provider HTTP, timeout, and OS network errors into a concise actionable message.
- Verification:
  - Added unit coverage for DDGS DNS recovery and hosted-model DNS error translation.
  - `python -m unittest discover -s tests -v`: passed 13 tests.
  - Fresh Streamlit server: HTTP 200 at `http://localhost:8503`.
- Follow-up: Refresh the browser and retry the research request; transient DNS failures now produce a recoverable response instead of a raw socket error.

## 2026-09-07 15:00 - Hugging Face Hosted Inference Adapter

- Status: passed
- Goal: Complete migration phase 2 by connecting the provider-neutral model boundary to Hugging Face Inference Providers.
- Scope: model adapters, model factory, environment template, tests, README, and live hosted inference.
- Evidence:
  - Installed `huggingface_hub==1.28.0` supports `InferenceClient.chat_completion()` with messages, model, provider, and token limits.
  - `HF_TOKEN` was present in the local `.env`; its value was not displayed or recorded.
- Changes:
  - Added `HuggingFaceInferenceChatModel` using the official synchronous `InferenceClient`.
  - Added environment-driven selection between `local` and `huggingface` backends.
  - Added `.env.example` with non-secret local and hosted configuration.
  - Kept local Transformers inference as the default and preserved the Streamlit/agent contract.
- Issues and fixes:
  - `Qwen/Qwen2.5-7B-Instruct` with automatic routing returned HTTP 400 `model_not_available` because Together required a dedicated endpoint.
  - `Qwen/Qwen2.5-7B-Instruct-1M` accepted an explicit `featherless-ai` request; the initial 12-token response contained only whitespace.
  - Tightened empty-response validation and increased the smoke-test token allowance.
  - Automatic routing for the replacement model returned HTTP 400 `model_not_supported` for the account's enabled providers, so `featherless-ai` became the tested configurable default.
- Verification:
  - Hosted request through `featherless-ai` returned a non-empty response successfully.
  - Unit coverage verifies hosted request mapping, response normalization, blank-response rejection, factory selection, and invalid backend handling.
  - `python -m unittest discover -s tests -v`: passed 11 tests.
  - `python -m compileall first_agent.py apps src tests`: passed.
  - `git diff --check`: passed.
- Follow-up: Preserve the Streamlit Sources behavior while introducing LangGraph around the existing research tools in migration phase 4.

## 2026-09-07 14:00 - Provider-Neutral Model Boundary

- Status: passed
- Goal: Complete migration phase 1 by removing direct Transformers inference from agent orchestration without changing user-facing behavior.
- Scope: `src/first_agent/models/`, `src/first_agent/agent.py`, exports, tests, and README.
- Changes:
  - Added a `ChatModel` protocol accepting chat messages and generation options.
  - Moved Hugging Face login, pipeline caching, local model loading, and response normalization into `TransformersChatModel`.
  - Injected the model adapter into `LocalChatAgent`; the local Transformers adapter remains the default for backward compatibility.
  - Preserved the CLI and Streamlit research contracts, including authoritative links and the collapsed Sources expander.
- Verification:
  - Existing 5-test suite passed immediately after the refactor.
  - Added focused coverage for adapter output normalization and plain-chat dependency injection.
  - `python -m unittest discover -s tests -v`: passed 7 tests.
  - `python -m compileall first_agent.py apps src tests`: passed.
  - `git diff --check`: passed.
- Operational note: Streamlit documentation discovery required the project Python executable, which Windows allowed only outside the restricted sandbox. This did not affect application tests.
- Follow-up: Add a Hugging Face Inference Providers adapter as migration phase 2, selected through configuration while retaining `TransformersChatModel` for local use.

## 2026-09-07 13:00 - Remove Duplicate Source Output

- Status: passed
- Goal: Show research citations only inside the compact Sources expander.
- Scope: agent response cleanup, Streamlit rendering, tests, and README.
- Changes:
  - Removed model-generated Sources, References, or Citations blocks before adding the authoritative tool links.
  - Applied the same cleanup while rendering existing chat history.
  - Kept the linked source list inside the collapsed Streamlit Sources expander.
- Verification:
  - `python -m unittest discover -s tests -v`: passed 5 tests, including duplicate-source cleanup.
  - Python compilation and `git diff --check`: passed.
  - Restarted Streamlit and received HTTP 200 at `http://localhost:8503`.
- Follow-up: none.

## 2026-09-07 12:20 - Research Tool Separation and Sources UI

- Status: passed
- Goal: Keep web research in a dedicated tool package, confirm agent integration, and make citations compact in the UI.
- Scope: `src/first_agent/tools/`, agent imports, Streamlit message rendering, tests, and README.
- Changes:
  - Moved web search and scraping into `src/first_agent/tools/web_research.py` with explicit package exports.
  - Added a collapsed Sources expander beneath research answers in Streamlit.
  - Added deterministic search-provider mapping coverage alongside the existing agent integration and scraper safety tests.
- Verification:
  - `python -m unittest discover -s tests -v`: passed 4 tests covering extraction, URL safety, search mapping, and agent integration.
  - Python compilation: passed for the CLI, Streamlit app, agent package, tool package, and tests.
  - Streamlit `AppTest`: returned zero app exceptions and exposed the Sources expander for a stored research response.
  - Live server: returned HTTP 200 at `http://localhost:8503` after restart.
- Operational note: Avoid running multiple Streamlit/AppTest processes with the local Transformers model simultaneously; the additional test process exited at the Windows process level during a redundant assertion run.
- Follow-up: Move the tool interface behind an MCP server and the agent behind FastAPI without changing the UI contract.

## 2026-09-07 11:00 - Research Agent Workflow

- Status: passed
- Goal: Turn the local chat agent into a keyless web research agent with concise, source-linked answers.
- Scope: agent orchestration, web search/scraping tools, Streamlit UI, tests, and documentation.
- Changes:
  - `src/first_agent/web_tools.py`: added DuckDuckGo search, public-URL validation, HTML extraction, and Jina Reader fallback.
  - `src/first_agent/agent.py`: added evidence-grounded research synthesis and source citation output.
  - `apps/streamlit_app.py`: added research controls and progress feedback while preserving the chat UI.
  - `tests/test_research_agent.py`: added extraction and orchestration coverage without live-network dependencies.
- Known constraints:
  - Keyless public search and reader services can rate-limit requests or change behavior.
  - The small local model may summarize less reliably than a hosted instruction model.
- Verification:
  - `python -m unittest discover -s tests -v`: passed 3 tests.
  - Live `WebResearchTools.research()` request: retrieved and extracted two public sources.
  - Live `LocalChatAgent.generate_research_reply()` request: generated an evidence-based summary with two source links.
  - Streamlit `AppTest`: rendered with zero exceptions and exposed the expected research controls and chat input.
- Follow-up: Move the same tool contracts behind FastAPI and MCP boundaries.

## 2026-08-24 08:25 - Streamlit UI Setup

- Status: fixed
- Symptom: User requested a Streamlit interface, future-ready folder structure, and an issue log.
- Scope: Project setup, Streamlit app, local Python environment.
- Suspected cause: The existing agent was a terminal-only script with model loading and input handling at module import time.
- Evidence:
  - `first_agent.py`: contained top-level Hugging Face login, model pipeline creation, and an infinite input loop.
  - `.venv\Scripts\python.exe`: returned `Access is denied` for the configured base Python path during sandboxed Streamlit docs discovery.
  - `Get-Command streamlit`: no installed Streamlit command found on PATH.
  - `Start-Process .venv\Scripts\streamlit.exe`: blocked by Windows Application Control policy.
- Changes:
  - `src/first_agent/agent.py`: added reusable local chat agent logic with cached Hugging Face pipeline loading.
  - `first_agent.py`: converted to a CLI entry point that uses the shared agent module.
  - `apps/streamlit_app.py`: added Streamlit chat UI for interacting with the agent.
  - `requirements.txt`: added Streamlit as an app dependency.
  - `assets/`, `skills/`, `mcp/`, `tools/`, `docs/`, `logs/`: added project folders for future code, supporting assets, and runtime logs.
  - `.venv`: installed `streamlit==1.62.0`.
- Verification:
  - `.venv\Scripts\python.exe --version`: passed with `Python 3.14.6` when run outside the sandbox.
  - `.venv\Scripts\python.exe -m compileall first_agent.py apps src`: passed.
  - `.venv\Scripts\python.exe -m pip show streamlit`: passed with `Version: 1.62.0`.
  - `python -m streamlit run apps/streamlit_app.py --server.port=8501`: launched the local app server as background process `79432`.
  - `Invoke-WebRequest http://localhost:8501`: passed with HTTP `200`.
  - `logs\streamlit.err.log`: recorded `Uvicorn server started on :::8501`.
- Follow-up:
  - Use `python -m streamlit run apps/streamlit_app.py` if Windows blocks the `streamlit.exe` launcher.
