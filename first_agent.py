from dotenv import load_dotenv
import os
from huggingface_hub import login
from transformers import pipeline

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
        response = pipe(chat, max_new_tokens=200)
        chat = response[0]["generated_text"]  # full history, including the new reply
        reply = chat[-1]["content"]

        print(f"\n🤖 Agent: {reply}\n")

    except KeyboardInterrupt:
        print("\n(Stopped) Goodbye!")
        break