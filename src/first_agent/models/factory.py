import os

from dotenv import load_dotenv

from .base import ChatModel
from .huggingface_inference import HuggingFaceInferenceChatModel
from .transformers import TransformersChatModel

LOCAL_BACKEND = "local"
HUGGINGFACE_BACKEND = "huggingface"
DEFAULT_LOCAL_MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"
DEFAULT_HOSTED_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct-1M"
DEFAULT_HOSTED_PROVIDER = "featherless-ai"


def get_chat_model_backend() -> str:
    load_dotenv()
    return os.getenv("CHAT_MODEL_BACKEND", LOCAL_BACKEND).strip().lower()


def get_default_model_id(backend: str | None = None) -> str:
    selected_backend = backend or get_chat_model_backend()
    if selected_backend == HUGGINGFACE_BACKEND:
        return os.getenv("HF_INFERENCE_MODEL_ID", DEFAULT_HOSTED_MODEL_ID)
    return os.getenv("HF_MODEL_ID", DEFAULT_LOCAL_MODEL_ID)


def create_chat_model(
    model_id: str | None = None,
    *,
    backend: str | None = None,
) -> ChatModel:
    load_dotenv()
    selected_backend = (backend or get_chat_model_backend()).strip().lower()
    selected_model = model_id or get_default_model_id(selected_backend)

    if selected_backend == LOCAL_BACKEND:
        return TransformersChatModel(selected_model)
    if selected_backend == HUGGINGFACE_BACKEND:
        return HuggingFaceInferenceChatModel(
            selected_model,
            token=os.getenv("HF_TOKEN", ""),
            provider=os.getenv("HF_INFERENCE_PROVIDER", DEFAULT_HOSTED_PROVIDER),
            timeout=float(os.getenv("HF_INFERENCE_TIMEOUT", "60")),
        )
    raise ValueError(
        f"Unsupported CHAT_MODEL_BACKEND '{selected_backend}'. "
        f"Expected '{LOCAL_BACKEND}' or '{HUGGINGFACE_BACKEND}'."
    )
