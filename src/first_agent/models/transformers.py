import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from huggingface_hub import login
from transformers import pipeline

from .base import ChatMessage


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


class TransformersChatModel:
    """Local chat-model adapter backed by a Transformers pipeline."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id

    def generate(
        self,
        messages: list[ChatMessage],
        *,
        max_new_tokens: int = 500,
        do_sample: bool = False,
    ) -> str:
        response = _get_pipeline(self.model_id)(
            messages,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
        )
        generated_text = response[0]["generated_text"]
        if isinstance(generated_text, list) and generated_text:
            return str(generated_text[-1].get("content", "")).strip()
        return str(generated_text).strip()

