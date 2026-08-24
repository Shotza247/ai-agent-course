# Audit Log — First Agent project

This file records issues, decisions, and fixes discovered during development of the First Agent and its Streamlit frontend. Treat this as the single point of truth for code-review findings and issue tracking for this repository.

Format (each entry):
- ID: unique short id
- Date: ISO 8601 timestamp (local)
- Severity: Critical / High / Medium / Low
- Affected files: list of files (path relative to repo root)
- Description: short description of the problem or observation
- Action taken: what was changed, with links to files where applicable
- Status: Open / Fixed / Mitigated / Won't fix
- Notes / Next steps: recommendations or follow-ups

---

## Entries

### ID: issue-001
- Date: 2026-08-23T19:38:20+02:00
- Severity: Medium
- Affected files:
  - first_agent.py
- Description: No Streamlit frontend existed; user requested a web UI to interact with the agent.
- Action taken: Added `streamlit_frontend.py` which loads the same model and exposes a text-area UI and chat history. Caches the transformers pipeline with @st.cache_resource to avoid reloading the model on each interaction.
  - File added: `streamlit_frontend.py`
- Status: Fixed
- Notes / Next steps: Consider adding streaming generation or token-by-token updates; optionally add authentication or usage limits if exposing on a shared host.

---

### ID: issue-002
- Date: 2026-08-23T19:55:52+02:00
- Severity: Low
- Affected files:
  - README.md
- Description: README lacked usage instructions for the new Streamlit frontend and general startup guidance was minimal.
- Action taken: Updated `README.md` to include setup, CLI usage, Streamlit usage and notes about HF_TOKEN and model choices.
- Status: Fixed
- Notes / Next steps: Keep README in sync if code moves or model changes.

---

### ID: issue-003
- Date: 2026-08-23T19:57:54+02:00
- Severity: Low
- Affected files:
  - requirements.txt
- Description: `streamlit` was not listed as a dependency, so installing requirements did not install Streamlit for the new frontend.
- Action taken: Appended `streamlit` to `requirements.txt`.
- Status: Fixed
- Notes / Next steps: Consider adding a developer extras file (requirements-dev.txt) for local tooling.

---

### ID: issue-004
- Date: 2026-08-24T07:13:18+02:00
- Severity: High
- Affected files:
  - first_agent.py
  - streamlit_frontend.py
- Description: The code assumed a specific transformers pipeline output shape (response[0]["generated_text"] being a list representing chat history). Some `transformers` versions or models return a string or different structure, causing parsing errors and confusing output (e.g. "#attachment:Pasted text #1" or other malformed responses).
- Action taken:
  - Rewrote the response-parsing logic in both `first_agent.py` and `streamlit_frontend.py` to:
    - Inspect the returned object safely (handle list/dict/string forms)
    - Support `generated_text` as either a list (chat history) or a string reply
    - Provide fallbacks and robust stringification when the structure is unexpected
  - Added timing (time.perf_counter) around model calls and displayed response times in seconds in both CLI and Streamlit UI.
- Status: Fixed / Mitigated
- Notes / Next steps:
  - If a model still returns an unexpected structure, capture and paste a raw example of the Python object so the parser can be extended.
  - Consider adding unit tests that simulate common pipeline outputs to prevent regressions.

---

### ID: issue-005
- Date: 2026-08-24T07:37:08+02:00
- Severity: High
- Affected files:
  - requirements.txt
  - README.md
- Description: Users encountered `ModuleNotFoundError: No module named 'torchvision'` at runtime. Some models or pipelines import torchvision indirectly.
- Action taken:
  - Added `torchvision` to `requirements.txt`.
  - Updated README to recommend installing both `torch` and `torchvision` from the PyTorch CPU wheel index for CPU-only machines and added troubleshooting commands for pip and conda.
- Status: Fixed / Mitigated
- Notes / Next steps: Keep torch/torchvision compatibility in mind — wheels must match the installed torch version. Consider pinning to compatible versions or using the official install instructions per environment.

---

### ID: issue-006
- Date: 2026-08-24T07:40:19+02:00
- Severity: Medium
- Affected files:
  - requirements.txt
  - first_agent.py
  - streamlit_frontend.py
- Description: Risk of torch/torchvision version mismatches which can lead to runtime ImportErrors or ABI incompatibilities.
- Action taken:
  - Pinned `torch==2.2.0` and `torchvision==0.17.0` in `requirements.txt` with a comment explaining these are CPU-friendly pins and should be changed for CUDA builds.
  - Added startup checks to both Python entrypoints (`first_agent.py`, `streamlit_frontend.py`) that attempt to `import torchvision` and provide a clear, actionable message if it's missing. The CLI script exits with a friendly message; the Streamlit app displays a warning and stops.
- Status: Fixed / Mitigated
- Notes / Next steps:
  - Optionally implement a runtime check that compares `torch.__version__` with `torchvision.__version__` and prints a specific mismatch message (recommended).
  - Optionally relax exact pins to ranges (e.g., `torch~=2.2`) depending on your compatibility policy.

---

## How to use this audit log as a code-review skill
1. When a new issue is found during review or testing, add a new entry below using the template above. Keep entries concise and factual.
2. Include affected file paths and any commands needed to reproduce the issue.
3. Mark status as `Open` if the problem still needs work, or `Fixed` once a PR has been merged and validated.
4. For high-severity findings, create a `todos` entry in the session DB or open a GitHub issue and reference it here.

## Suggested improvements (future)
- Add a small script (or CLI command) to append audit entries automatically from the terminal or CI.
- Integrate with the repo's issue tracker: create GitHub issues for `High`/`Critical` entries and store the issue number in this log.
- Add automated runtime compatibility checks to CI (verify torch/torchvision version, basic import smoke tests for transformers, streamlit, etc.).

---

_Last update: 2026-08-24T08:01:22+02:00_
