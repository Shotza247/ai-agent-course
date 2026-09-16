import unittest

from src.first_agent.memory import (
    InMemoryLongTermMemory,
    MemoryRecord,
    create_short_term_memory,
)
from src.first_agent.skills import ResearchSynthesisSkill
from src.first_agent.tools import ResearchSource
from src.first_agent.workflows import ResearchWorkflow


class FakeResearchTools:
    def __init__(self, sources: list[ResearchSource]) -> None:
        self.sources = sources

    def research(self, query: str, max_sources: int = 3) -> list[ResearchSource]:
        return self.sources[:max_sources]


class FakeChatModel:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, messages, *, max_new_tokens=500, do_sample=False) -> str:
        self.calls += 1
        return "A grounded summary."


class ResearchWorkflowTests(unittest.TestCase):
    def test_workflow_checkpoints_a_successful_research_run(self) -> None:
        source = ResearchSource(
            title="Primary source",
            url="https://example.com/report",
            content="Verified evidence.",
        )
        model = FakeChatModel()
        workflow = ResearchWorkflow(
            research_tools=FakeResearchTools([source]),
            chat_model=model,
            synthesis_skill=ResearchSynthesisSkill(),
            checkpointer=create_short_term_memory(),
        )

        result = workflow.run(
            chat_history=[{"role": "system", "content": "Research carefully."}],
            user_input="test topic",
            max_new_tokens=120,
            max_sources=1,
            thread_id="thread-1",
        )

        self.assertIn("A grounded summary.", result["reply"])
        self.assertIn("https://example.com/report", result["reply"])
        self.assertEqual(model.calls, 1)
        self.assertEqual(workflow.get_state("thread-1").values["reply"], result["reply"])

    def test_workflow_skips_model_when_no_sources_are_found(self) -> None:
        model = FakeChatModel()
        workflow = ResearchWorkflow(
            research_tools=FakeResearchTools([]),
            chat_model=model,
            synthesis_skill=ResearchSynthesisSkill(),
            checkpointer=create_short_term_memory(),
        )

        result = workflow.run(
            chat_history=[],
            user_input="unknown topic",
            max_new_tokens=120,
            max_sources=2,
            thread_id="thread-2",
        )

        self.assertIn("could not retrieve", result["reply"])
        self.assertEqual(model.calls, 0)

    def test_long_term_memory_is_namespaced(self) -> None:
        memory = InMemoryLongTermMemory()
        saved = MemoryRecord(
            namespace=("user-1", "research"),
            kind="saved_topic",
            value={"topic": "LangGraph"},
        )
        memory.put(saved)

        self.assertEqual(memory.list(("user-1", "research")), [saved])
        self.assertEqual(memory.list(("user-2", "research")), [])

        memory.delete(saved.namespace, saved.memory_id)
        self.assertEqual(memory.list(saved.namespace), [])


if __name__ == "__main__":
    unittest.main()
