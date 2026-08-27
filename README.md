# First Agent

This project contains a lightweight local LLM agent, a reusable Python service
layer, a FastAPI HTTP service, and a Streamlit web frontend for it.

## Setup

Create a virtual environment:

```
py -m venv .venv
```

Activate it:

```
.venv\Scripts\Activate.ps1
```

Install PyTorch first. This is required before `transformers` can load the model.

If your laptop does not have a dedicated NVIDIA GPU, install the lighter CPU-only
build:

```
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

If you still see an error like `ModuleNotFoundError: No module named 'torchvision'`,
install torchvision with a matching wheel for your PyTorch version:

```
pip install torchvision --index-url https://download.pytorch.org/whl/cpu
```

If you use conda, you can also install with:

```
conda install -c pytorch torchvision
```

If you do have an NVIDIA GPU and want CUDA acceleration, use the command generator at
https://pytorch.org/get-started/locally/ instead.

Install the rest of the project dependencies:

```
pip install -r requirements.txt
```

Verify the setup:

```
py -c "import torch, transformers; print('The setup was successful, PyTorch:', torch.__version__)"
```

You should see something like: `The setup was successful, PyTorch: 2.x.x`

## Run the CLI agent

```
py first_agent.py
```

This starts a terminal-based chat loop using the `HuggingFaceTB/SmolLM2-360M-Instruct`
model. The CLI is a thin wrapper around the reusable `FirstAgent` service.

## Reuse the agent from other apps

`first_agent.py` is import-safe: importing it does not start the terminal chat loop or
load the model immediately. You can use the same service layer from FastAPI, Streamlit,
tests, notebooks, or future JavaScript/React-backed APIs.

```python
from first_agent import FirstAgent

agent = FirstAgent()
chat = agent.new_chat()
result = agent.respond("Hello!", chat=chat)

print(result.reply)
chat = result.chat
```

Useful exports:
- `FirstAgent`: reusable service object with lazy model loading.
- `initial_chat()`: creates a fresh chat history.
- `AgentResponse`: structured response containing `chat`, `reply`, and elapsed time.
- `DEFAULT_MODEL_ID`: the shared model identifier.

## Run the FastAPI service

```
uvicorn agent_api:app --reload --port 8000
```

The API exposes:

- `GET /health`: returns service status and the configured model id.
- `POST /chat`: accepts a user message and optional chat history, then returns the
  assistant reply and updated chat history.

Example request:

```json
{
  "message": "Hello!",
  "chat": [
    {"role": "system", "content": "You are a helpful, concise assistant."}
  ]
}
```

The service is stateless. The client sends the current chat history with each request,
which keeps it straightforward for Streamlit, React, or any other frontend.

## Run the Streamlit frontend

Start the FastAPI service first, then run:

```
streamlit run streamlit_frontend.py
```

Then open the local URL shown in the terminal, usually `http://localhost:8501`.
By default the Streamlit app calls `http://localhost:8000`. You can point it to a
different backend with the sidebar field or by setting `AGENT_API_URL`.

The frontend lets you:
- send prompts through a chat interface
- call the FastAPI-backed agent endpoint
- clear the conversation
- check the backend status

## Notes

- `HF_TOKEN` in a `.env` file is optional. It is only needed for gated/private models
  or to raise your Hugging Face API rate limits. The model used here is public.
- The original script pointed at `deepseek-ai/DeepSeek-V4-Pro-0813`, which is a
  1.57-trillion-parameter server-scale model and not something a laptop can load
  locally. `first_agent.py` now uses a ~360M-parameter model instead, which downloads
  quickly and runs on CPU.
- If you want noticeably better answers and do not mind a slower first load, pass a
  different `model_id` to `FirstAgent`, such as `"Qwen/Qwen2.5-0.5B-Instruct"` or
  `"HuggingFaceTB/SmolLM2-1.7B-Instruct"`.
- The CLI and FastAPI service use the same reusable service layer instead of duplicating
  model and response-parsing logic.
- The Streamlit app talks to FastAPI over HTTP, which mirrors how a future React
  application can consume the same agent.
