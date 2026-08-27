# First Agent

This project contains a lightweight local LLM agent and a Streamlit web frontend for it.

## Setup

Create a virtual environment:
```
py -m venv .venv
```

Activate it:
```
.venv\Scripts\Activate.ps1
```

Install PyTorch first (this is required before `transformers` can load the model):

If your laptop does **not** have a dedicated NVIDIA GPU (most laptops), install the
lighter CPU-only build:
```
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

If you still see an error like `ModuleNotFoundError: No module named 'torchvision'`, install torchvision with a matching wheel for your PyTorch version. For CPU-only environments the command above should work; alternatively run:
```
pip install torchvision --index-url https://download.pytorch.org/whl/cpu
```
If you use conda you can also install with:
```
conda install -c pytorch torchvision
```

If you *do* have an NVIDIA GPU and want CUDA acceleration, use the command generator at
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
model.

## Run the Streamlit frontend

``` 
streamlit run streamlit_frontend.py
```

Then open the local URL shown in the terminal (usually `http://localhost:8501`).

The frontend lets you:
- send prompts in a text box
- view the chat history in the browser
- clear the conversation
- interact with the same model used by `first_agent.py`

## Notes

- `HF_TOKEN` in a `.env` file is optional — it's only needed for gated/private models
  or to raise your Hugging Face API rate limits. The model used here is public.
- The original script pointed at `deepseek-ai/DeepSeek-V4-Pro-0813`, which is a
  1.57-trillion-parameter server-scale model — not something a laptop can load locally.
  `first_agent.py` now uses a ~360M-parameter model instead, which downloads quickly and
  runs on CPU. If you want noticeably better answers and don't mind a slower first load,
  swap `MODEL_ID` for `"Qwen/Qwen2.5-0.5B-Instruct"` or `"HuggingFaceTB/SmolLM2-1.7B-Instruct"`.
- The Streamlit app uses the same `MODEL_ID` and chat pattern as the CLI version, but
  wraps it in a web interface.