from dotenv import load_dotenv
import os
import sys
from huggingface_hub import login
from transformers import pipeline

# Friendly check for torchvision, which some models/pipelines import indirectly.
# If missing, give a clear install hint and exit early to avoid confusing tracebacks.
try:
    import torchvision  # noqa: F401
except ImportError:
    print("ERROR: Missing dependency 'torchvision'. Some models or pipeline code require torchvision.")
    print("If you're on a CPU-only machine, run:\n  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu")
    print("Or use the command from https://pytorch.org/get-started/locally/ appropriate for your platform.")
    sys.exit(1)

# 1. Load .env file (contains your HF_TOKEN) — optional for public models
load_dotenv()
hf_token = os.getenv("HF_TOKEN")
if hf_token:
    login(token=hf_token)
else:
    print("ℹ️  No HF_TOKEN set — continuing without login (fine for public models).\n")

# 2. A small, free instruct model that actually runs on a laptop CPU
#    (DeepSeek-V4-Pro is a 1.57T-parameter server-scale model — way too big to load here)
MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"

# 3. Create a local text-generation pipeline (chat-capable)
#    Note: "text2text-generation" was removed in transformers v5 — "text-generation"
#    now handles both plain and chat-style generation.
print(f"⏳ Loading {MODEL_ID} (first run downloads the model, ~1-2 min)...")
pipe = pipeline(
    task="text-generation",
    model=MODEL_ID,
    dtype="auto",
)

print("✅ Agent ready! Type a question, or 'quit' to stop.\n")

# Chat history, in the {"role": ..., "content": ...} format the pipeline expects
chat = [
    {"role": "system", "content": "You are a helpful, concise assistant."}
]

while True:
    try:
        user_input = input("> ").strip()
        if user_input.lower() in {"quit", "exit"}:
            print("Goodbye!")
            break
        if not user_input:
            continue

        chat.append({"role": "user", "content": user_input})
        from time import perf_counter
        start = perf_counter()
        try:
            response = pipe(chat, max_new_tokens=200)
        except Exception as e:
            print(f"Model error: {e}")
            continue
        elapsed = perf_counter() - start

        # Robustly parse the pipeline response. Different transformers versions/models
        # return different structures: sometimes `generated_text` is a list (chat history),
        # sometimes it's a single string. Handle both.
        reply = None
        try:
            first = response[0] if isinstance(response, list) else response
            gen = None
            if isinstance(first, dict):
                gen = first.get("generated_text") or first.get("text") or first.get("summary_text")
            else:
                gen = first

            if isinstance(gen, list):
                # full chat history returned
                chat = gen
                last = chat[-1]
                if isinstance(last, dict):
                    reply = last.get("content") or last.get("text")
                else:
                    reply = str(last)
            elif isinstance(gen, str):
                # single-string reply; append as assistant message
                reply = gen
                chat.append({"role": "assistant", "content": reply})
            else:
                # fallback: stringify response
                reply = str(response)
                chat.append({"role": "assistant", "content": reply})
        except Exception as e:
            reply = f"(Could not parse model response: {e})"
            chat.append({"role": "assistant", "content": reply})

        print(f"\n🤖 Agent: {reply}\n")
        print(f"(Response time: {elapsed:.2f} seconds)\n")

    except KeyboardInterrupt:
        print("\n(Stopped) Goodbye!")
        break