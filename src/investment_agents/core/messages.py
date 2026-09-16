from __future__ import annotations

DEFAULT_MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"
DEFAULT_SYSTEM_PROMPT = """You are an expert market analysts who continously monitors daily market trends, and sentiments and cross checks them with 52-week highs, moving averages and other market related triggers and political and economic trends and shifts that will impact market volatility. Clearly state when the sources do not contain enough evidence."""
DEFAULT_MAX_NEW_TOKENS = 300

ChatMessage = dict[str, str]


def initial_chat(system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> list[ChatMessage]:
    """Create a fresh chat history in the format expected by chat clients."""
    return [{"role": "system", "content": system_prompt}]
