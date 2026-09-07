from typing import Any

from huggingface_hub import InferenceClient

from .base import ChatMessage


class HuggingFaceInferenceChatModel:
    """Hosted chat-model adapter using Hugging Face Inference Providers."""

    def __init__(
        self,
        model_id: str,
        *,
        token: str,
        provider: str = "auto",
        timeout: float = 60.0,
        client: Any | None = None,
    ) -> None:
        if not token:
            raise ValueError("HF_TOKEN is required for Hugging Face hosted inference.")
        self.model_id = model_id
        self.provider = provider
        self._client = client or InferenceClient(
            provider=provider,
            api_key=token,
            timeout=timeout,
        )

    def generate(
        self,
        messages: list[ChatMessage],
        *,
        max_new_tokens: int = 200,
        do_sample: bool = False,
    ) -> str:
        completion = self._client.chat_completion(
            messages,
            model=self.model_id,
            max_tokens=max_new_tokens,
            temperature=None if do_sample else 0.0,
        )
        content = completion.choices[0].message.content
        normalized_content = str(content or "").strip()
        if not normalized_content:
            raise RuntimeError("Hugging Face inference returned an empty response.")
        return normalized_content
