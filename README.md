Set-up a virtual Env
```
py -m venv .venv
```

Activate the Env
```
.venv\Scripts\Activate.ps1
```

Install PyTorch first (this is the piece the original setup was missing — `transformers`
can't load any model without it).

If your laptop does **not** have a dedicated NVIDIA GPU (most laptops), install the
lighter CPU-only build:
```
pip install torch --index-url https://download.pytorch.org/whl/cpu
```
If you *do* have an NVIDIA GPU and want CUDA acceleration, use the command generator at
https://pytorch.org/get-started/locally/ instead.

Install the rest of the libraries
```
pip install -r requirements.txt
```

Verify that everything is in place
```
py -c "import torch, transformers; print('The setup was successful, PyTorch:', torch.__version__)"
```

You should see something like: "The setup was successful, PyTorch: 2.x.x"

Run the agent
```
py first_agent.py
```

Notes
- `HF_TOKEN` in a `.env` file is optional now — it's only needed for gated/private models
  or to raise your Hugging Face API rate limits. The model used in `first_agent.py`
  (`HuggingFaceTB/SmolLM2-360M-Instruct`) is public.
- The original script pointed at `deepseek-ai/DeepSeek-V4-Pro-0813`, which is a
  1.57-trillion-parameter server-scale model — not something a laptop can load locally.
  `first_agent.py` now uses a ~360M-parameter model instead, which downloads quickly and
  runs on CPU. If you want noticeably better answers and don't mind a slower first load,
  swap `MODEL_ID` for `"Qwen/Qwen2.5-0.5B-Instruct"` or `"HuggingFaceTB/SmolLM2-1.7B-Instruct"`.