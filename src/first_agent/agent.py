import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from huggingface_hub import login
from transformers import pipeline

DEFAULT_MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"
DEFAULT_SYSTEM_PROMPT = "You are a helpful, concise assistant, getting real-time data from the internet."


@lru_cache(maxsize=1)
def _login_to_huggingface() -> None:
    load_dotenv()
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        login(token=hf_token)


@lru_cache(maxsize=4)
def _get_pipeline(model_id: str) -> Any:
    _login_to_huggingface()
    return pipeline(
        task="text-generation",
        model=model_id,
        dtype="auto",
    )


class LocalChatAgent:
    def __init__(
        self,
        model_id: str | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self.model_id = model_id or os.getenv("HF_MODEL_ID", DEFAULT_MODEL_ID)
        self.system_prompt = system_prompt

    def new_chat(self) -> list[dict[str, str]]:
        return [{"role": "system", "content": self.system_prompt}]

    def generate_reply(
        self,
        chat_history: list[dict[str, str]],
        user_input: str,
        max_new_tokens: int = 200,
    ) -> tuple[str, list[dict[str, str]]]:
        messages = [*chat_history, {"role": "user", "content": user_input}]
        response = _get_pipeline(self.model_id)(messages, max_new_tokens=max_new_tokens)
        generated_text = response[0]["generated_text"]

        if isinstance(generated_text, list) and generated_text:
            reply = generated_text[-1].get("content", "")
            return reply, generated_text

        reply = str(generated_text)
        return reply, [*messages, {"role": "assistant", "content": reply}]
