# AI Agent Course

## Setup

Create a virtual environment:

```powershell
py -m venv .venv
```

Activate the environment:

```powershell
.venv\Scripts\Activate.ps1
```

Install PyTorch first. `transformers` needs a backend such as PyTorch to load models.

For CPU-only laptops:

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

For NVIDIA GPU acceleration, use the command generator at:

https://pytorch.org/get-started/locally/

Install the rest of the libraries:

```powershell
pip install -r requirements.txt
```

Verify that everything is in place:

```powershell
py -c "import torch, transformers; print('The setup was successful, PyTorch:', torch.__version__)"
```

You should see something like: `The setup was successful, PyTorch: 2.x.x`

## Run

Run the terminal agent:

```powershell
py first_agent.py
```

Run the Streamlit UI:

```powershell
streamlit run apps/streamlit_app.py
```

## Project Structure

- `apps/`: user interfaces and runnable app entry points.
- `src/first_agent/`: reusable agent code shared by the CLI and Streamlit UI.
- `assets/`: images, documents, and static assets.
- `skills/`: future custom agent skills.
- `mcp/`: future MCP server configuration and setup notes.
- `tools/`: future tool integrations and helper scripts.
- `docs/`: project notes and documentation.
- `logs/`: local runtime logs for app processes.
- `audit_log.md`: running issue and recovery log.

## Notes

- `HF_TOKEN` in a `.env` file is optional. It is only needed for gated/private models or to raise Hugging Face API rate limits.
- The model used by default is `HuggingFaceTB/SmolLM2-360M-Instruct`, which is public and small enough to run locally.
- The original script pointed at `deepseek-ai/DeepSeek-V4-Pro-0813`, which is a 1.57-trillion-parameter server-scale model and not practical to load on a laptop.
- If you want noticeably better answers and do not mind a slower first load, set `HF_MODEL_ID` or use the Streamlit sidebar to try `Qwen/Qwen2.5-0.5B-Instruct` or `HuggingFaceTB/SmolLM2-1.7B-Instruct`.
