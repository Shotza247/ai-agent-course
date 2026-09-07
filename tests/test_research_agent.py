import unittest
from unittest.mock import patch

from src.first_agent.agent import LocalChatAgent
from src.first_agent.models import TransformersChatModel
from src.first_agent.tools import ResearchSource, WebResearchTools


class FakeResearchTools:
    def research(self, query: str, max_sources: int = 3) -> list[ResearchSource]:
        assert query == "test topic"
        assert max_sources == 2
        return [
            ResearchSource(
                title="Primary source",
                url="https://example.com/report",
                content="The verified result is 42.",
            )
        ]


class FakeChatModel:
    def __init__(self, reply: str = "The result is 42.") -> None:
        self.reply = reply
        self.calls: list[tuple[list[dict[str, str]], int, bool]] = []

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        max_new_tokens: int = 200,
        do_sample: bool = False,
    ) -> str:
        self.calls.append((messages, max_new_tokens, do_sample))
        return self.reply


class ResearchAgentTests(unittest.TestCase):
    @patch("src.first_agent.models.transformers._get_pipeline")
    def test_transformers_adapter_normalizes_chat_output(self, get_pipeline) -> None:
        get_pipeline.return_value.return_value = [
            {"generated_text": [{"role": "assistant", "content": "Adapter reply"}]}
        ]

        reply = TransformersChatModel("test/model").generate(
            [{"role": "user", "content": "Hello"}],
            max_new_tokens=64,
        )

        self.assertEqual(reply, "Adapter reply")
        get_pipeline.assert_called_once_with("test/model")
        get_pipeline.return_value.assert_called_once_with(
            [{"role": "user", "content": "Hello"}],
            max_new_tokens=64,
            do_sample=False,
        )

    @patch("src.first_agent.tools.web_research.DDGS")
    @patch.object(WebResearchTools, "_is_public_http_url", return_value=True)
    def test_search_web_maps_provider_results(self, _is_public_url, ddgs) -> None:
        ddgs.return_value.text.return_value = [
            {
                "title": "Example report",
                "href": "https://example.com/report",
                "body": "A useful result.",
            }
        ]

        results = WebResearchTools().search_web("test query", max_results=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Example report")
        self.assertEqual(results[0].url, "https://example.com/report")
        ddgs.return_value.text.assert_called_once_with(
            "test query",
            region="wt-wt",
            safesearch="moderate",
            max_results=1,
        )

    def test_html_to_text_removes_non_content_elements(self) -> None:
        html = "<main><h1>Useful</h1><p>Evidence</p></main><script>ignore()</script>"
        self.assertEqual(WebResearchTools._html_to_text(html), "Useful Evidence")

    def test_research_reply_preserves_question_and_adds_sources(self) -> None:
        chat_model = FakeChatModel()
        agent = LocalChatAgent(
            research_tools=FakeResearchTools(),
            chat_model=chat_model,
        )
        reply, history = agent.generate_research_reply(
            agent.new_chat(),
            "test topic",
            max_sources=2,
        )

        self.assertTrue(reply.startswith("The result is 42."))
        self.assertIn("[Primary source](https://example.com/report)", reply)
        self.assertEqual(history[-2], {"role": "user", "content": "test topic"})
        self.assertEqual(history[-1]["content"], reply)
        self.assertEqual(len(chat_model.calls), 1)
        self.assertIn("The verified result is 42.", chat_model.calls[0][0][-1]["content"])

    def test_private_urls_are_rejected(self) -> None:
        self.assertFalse(WebResearchTools._is_public_http_url("http://127.0.0.1/admin"))
        self.assertFalse(WebResearchTools._is_public_http_url("file:///etc/passwd"))

    def test_model_generated_sources_are_removed(self) -> None:
        summary = (
            "A concise researched answer.\n\n"
            "### Sources\n"
            "- Duplicate source text\n"
        )
        self.assertEqual(
            LocalChatAgent._strip_generated_sources(summary),
            "A concise researched answer.",
        )

    def test_plain_chat_uses_injected_model(self) -> None:
        chat_model = FakeChatModel("Hello from the adapter.")
        agent = LocalChatAgent(chat_model=chat_model)

        reply, history = agent.generate_reply(agent.new_chat(), "Hello")

        self.assertEqual(reply, "Hello from the adapter.")
        self.assertEqual(history[-1], {"role": "assistant", "content": reply})
        self.assertEqual(chat_model.calls[0][0][-1], {"role": "user", "content": "Hello"})


if __name__ == "__main__":
    unittest.main()
