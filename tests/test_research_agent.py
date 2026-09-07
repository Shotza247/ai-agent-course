import unittest
from unittest.mock import patch

from src.first_agent.agent import LocalChatAgent
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


class ResearchAgentTests(unittest.TestCase):
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
        agent = LocalChatAgent(research_tools=FakeResearchTools())
        model_response = [
            {"generated_text": [{"role": "assistant", "content": "The result is 42."}]}
        ]

        with patch("src.first_agent.agent._get_pipeline") as get_pipeline:
            get_pipeline.return_value.return_value = model_response
            reply, history = agent.generate_research_reply(
                agent.new_chat(),
                "test topic",
                max_sources=2,
            )

        self.assertTrue(reply.startswith("The result is 42."))
        self.assertIn("[Primary source](https://example.com/report)", reply)
        self.assertEqual(history[-2], {"role": "user", "content": "test topic"})
        self.assertEqual(history[-1]["content"], reply)

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


if __name__ == "__main__":
    unittest.main()
