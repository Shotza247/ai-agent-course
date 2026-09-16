from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from ..models import ChatModel
from ..skills import ResearchSynthesisSkill
from ..tools import ResearchSource, WebResearchTools
from .state import ResearchState


class ResearchWorkflow:
    """Deterministic LangGraph orchestration for the base research agent."""

    def __init__(
        self,
        research_tools: WebResearchTools,
        chat_model: ChatModel,
        synthesis_skill: ResearchSynthesisSkill,
        checkpointer: BaseCheckpointSaver,
    ) -> None:
        self.research_tools = research_tools
        self.chat_model = chat_model
        self.synthesis_skill = synthesis_skill
        self.graph = self._build_graph().compile(checkpointer=checkpointer)

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(ResearchState)
        builder.add_node("search_sources", self._search_sources)
        builder.add_node("prepare_evidence", self._prepare_evidence)
        builder.add_node("synthesize_answer", self._synthesize_answer)
        builder.add_node("finalize_answer", self._finalize_answer)
        builder.add_node("handle_no_sources", self._handle_no_sources)
        builder.add_edge(START, "search_sources")
        builder.add_conditional_edges(
            "search_sources",
            self._route_after_search,
            {"sources_found": "prepare_evidence", "no_sources": "handle_no_sources"},
        )
        builder.add_edge("prepare_evidence", "synthesize_answer")
        builder.add_edge("synthesize_answer", "finalize_answer")
        builder.add_edge("finalize_answer", END)
        builder.add_edge("handle_no_sources", END)
        return builder

    def run(
        self,
        *,
        chat_history: list[dict[str, str]],
        user_input: str,
        max_new_tokens: int,
        max_sources: int,
        thread_id: str,
    ) -> ResearchState:
        initial_state: ResearchState = {
            "chat_history": chat_history,
            "user_input": user_input,
            "max_new_tokens": max_new_tokens,
            "max_sources": max_sources,
            "sources": [],
            "research_prompt": "",
            "summary": "",
            "reply": "",
            "updated_history": chat_history,
            "error": None,
        }
        return self.graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}},
        )

    def get_state(self, thread_id: str):
        return self.graph.get_state({"configurable": {"thread_id": thread_id}})

    def _search_sources(self, state: ResearchState) -> dict[str, object]:
        sources = self.research_tools.research(
            state["user_input"], max_sources=state["max_sources"]
        )
        return {
            "sources": [
                {"title": source.title, "url": source.url, "content": source.content}
                for source in sources
            ]
        }

    @staticmethod
    def _route_after_search(state: ResearchState) -> str:
        return "sources_found" if state["sources"] else "no_sources"

    def _prepare_evidence(self, state: ResearchState) -> dict[str, str]:
        return {
            "research_prompt": self.synthesis_skill.build_prompt(
                state["user_input"], self._as_sources(state)
            )
        }

    def _synthesize_answer(self, state: ResearchState) -> dict[str, str]:
        messages = [
            *state["chat_history"],
            {"role": "user", "content": state["research_prompt"]},
        ]
        return {
            "summary": self.chat_model.generate(
                messages,
                max_new_tokens=state["max_new_tokens"],
                do_sample=False,
            )
        }

    def _finalize_answer(self, state: ResearchState) -> dict[str, object]:
        reply = self.synthesis_skill.format_reply(
            state["summary"], self._as_sources(state)
        )
        return {
            "reply": reply,
            "updated_history": [
                *state["chat_history"],
                {"role": "user", "content": state["user_input"]},
                {"role": "assistant", "content": reply},
            ],
        }

    @staticmethod
    def _as_sources(state: ResearchState) -> list[ResearchSource]:
        return [ResearchSource(**source) for source in state["sources"]]

    @staticmethod
    def _handle_no_sources(state: ResearchState) -> dict[str, object]:
        reply = (
            "I could not retrieve reliable public sources for that request. "
            "Try making the topic more specific or try again shortly."
        )
        return {
            "reply": reply,
            "updated_history": [
                *state["chat_history"],
                {"role": "user", "content": state["user_input"]},
                {"role": "assistant", "content": reply},
            ],
        }
