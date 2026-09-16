from typing import NotRequired, TypedDict

from ..models import ChatMessage


class ResearchSourceState(TypedDict):
    title: str
    url: str
    content: str


class ResearchState(TypedDict):
    chat_history: list[ChatMessage]
    user_input: str
    max_new_tokens: int
    max_sources: int
    sources: list[ResearchSourceState]
    research_prompt: str
    summary: str
    reply: str
    updated_history: list[ChatMessage]
    error: NotRequired[str | None]
