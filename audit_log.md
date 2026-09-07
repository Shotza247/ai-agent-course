# Audit Log

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
