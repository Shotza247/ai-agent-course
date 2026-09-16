from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver


def create_short_term_memory() -> BaseCheckpointSaver:
    """Create thread-scoped workflow memory for local development and tests."""
    return InMemorySaver()
