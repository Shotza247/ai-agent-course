from typing import Protocol


ChatMessage = dict[str, str]


class ChatModel(Protocol):
    """Provider-neutral text generation contract used by chat agents."""

    def generate(
        self,
        messages: list[ChatMessage],
        *,
        max_new_tokens: int = 200,
        do_sample: bool = False,
    ) -> str:
        """Generate one assistant response for a chat history."""

