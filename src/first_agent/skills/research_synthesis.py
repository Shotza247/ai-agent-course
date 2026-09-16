import re

from ..prompts import build_research_prompt
from ..tools import ResearchSource


class ResearchSynthesisSkill:
    """Reusable prompt and response rules for evidence-grounded research."""

    source_separator = "\n\n**Sources**\n"

    def build_prompt(self, question: str, sources: list[ResearchSource]) -> str:
        return build_research_prompt(question, sources)

    @staticmethod
    def strip_generated_sources(summary: str) -> str:
        source_heading = re.compile(
            r"\n\s*(?:#{1,6}\s*)?(?:\*\*)?"
            r"(?:sources?|references?|citations?)(?:\*\*)?\s*:?\s*\n",
            flags=re.IGNORECASE,
        )
        match = source_heading.search(summary)
        return summary[: match.start()].rstrip() if match else summary.strip()

    def format_reply(self, summary: str, sources: list[ResearchSource]) -> str:
        source_links = "\n".join(
            f"- [{source.title}]({source.url})" for source in sources
        )
        return f"{self.strip_generated_sources(summary)}{self.source_separator}{source_links}"
