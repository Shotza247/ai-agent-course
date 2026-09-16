"""Backward-compatible imports for the research-agent facade."""

from .agents.research_agent import DEFAULT_MODEL_ID, LocalChatAgent
from .config import DEFAULT_SYSTEM_PROMPT

__all__ = ["DEFAULT_MODEL_ID", "DEFAULT_SYSTEM_PROMPT", "LocalChatAgent"]
