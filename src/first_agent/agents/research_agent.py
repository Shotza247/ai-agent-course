from uuid import uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver

from ..config import DEFAULT_SYSTEM_PROMPT
from ..memory import create_short_term_memory
from ..models import ChatModel, create_chat_model, get_default_model_id
from ..skills import ResearchSynthesisSkill
from ..tools import ResearchSource, WebResearchTools
from ..workflows import ResearchWorkflow

DEFAULT_MODEL_ID = get_default_model_id()


class LocalChatAgent:
    """Public facade for chat and orchestrated web-research workflows."""

    def __init__(
        self,
        model_id: str | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        research_tools: WebResearchTools | None = None,
        chat_model: ChatModel | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self.model_id = model_id or get_default_model_id()
        self.system_prompt = system_prompt
        self.research_tools = research_tools or WebResearchTools()
        self.chat_model = chat_model or create_chat_model(self.model_id)
        self.synthesis_skill = ResearchSynthesisSkill()
        self._default_thread_id = str(uuid4())
        self.workflow = ResearchWorkflow(
            research_tools=self.research_tools,
            chat_model=self.chat_model,
            synthesis_skill=self.synthesis_skill,
            checkpointer=checkpointer or create_short_term_memory(),
        )

    def new_chat(self) -> list[dict[str, str]]:
        return [{"role": "system", "content": self.system_prompt}]

    def new_thread_id(self) -> str:
        return str(uuid4())

    def generate_reply(
        self,
        chat_history: list[dict[str, str]],
        user_input: str,
        max_new_tokens: int = 500,
    ) -> tuple[str, list[dict[str, str]]]:
        messages = [*chat_history, {"role": "user", "content": user_input}]
        reply = self.chat_model.generate(messages, max_new_tokens=max_new_tokens)
        return reply, [*messages, {"role": "assistant", "content": reply}]

    def generate_research_reply(
        self,
        chat_history: list[dict[str, str]],
        user_input: str,
        max_new_tokens: int = 500,
        max_sources: int = 3,
        thread_id: str | None = None,
    ) -> tuple[str, list[dict[str, str]]]:
        result = self.workflow.run(
            chat_history=chat_history,
            user_input=user_input,
            max_new_tokens=max_new_tokens,
            max_sources=max_sources,
            thread_id=thread_id or self._default_thread_id,
        )
        return result["reply"], result["updated_history"]

    def get_research_state(self, thread_id: str):
        return self.workflow.get_state(thread_id)

    @staticmethod
    def _strip_generated_sources(summary: str) -> str:
        return ResearchSynthesisSkill.strip_generated_sources(summary)

    @staticmethod
    def _build_research_prompt(question: str, sources: list[ResearchSource]) -> str:
        return ResearchSynthesisSkill().build_prompt(question, sources)
