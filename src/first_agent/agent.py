import os
import re
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from huggingface_hub import login
from transformers import pipeline

from .tools import ResearchSource, WebResearchTools

DEFAULT_MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"
DEFAULT_SYSTEM_PROMPT = (
    "You are a concise research assistant. Answer only from the supplied web research. "
    "Clearly state when the sources do not contain enough evidence."
)


@lru_cache(maxsize=1)
def _login_to_huggingface() -> None:
    load_dotenv()
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        login(token=hf_token)


@lru_cache(maxsize=4)
def _get_pipeline(model_id: str) -> Any:
    _login_to_huggingface()
    return pipeline(
        task="text-generation",
        model=model_id,
        dtype="auto",
    )


class LocalChatAgent:
    def __init__(
        self,
        model_id: str | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        research_tools: WebResearchTools | None = None,
    ) -> None:
        self.model_id = model_id or os.getenv("HF_MODEL_ID", DEFAULT_MODEL_ID)
        self.system_prompt = system_prompt
        self.research_tools = research_tools or WebResearchTools()

    def new_chat(self) -> list[dict[str, str]]:
        return [{"role": "system", "content": self.system_prompt}]

    def generate_reply(
        self,
        chat_history: list[dict[str, str]],
        user_input: str,
        max_new_tokens: int = 200,
    ) -> tuple[str, list[dict[str, str]]]:
        messages = [*chat_history, {"role": "user", "content": user_input}]
        response = _get_pipeline(self.model_id)(messages, max_new_tokens=max_new_tokens)
        generated_text = response[0]["generated_text"]

        if isinstance(generated_text, list) and generated_text:
            reply = generated_text[-1].get("content", "")
            return reply, generated_text

        reply = str(generated_text)
        return reply, [*messages, {"role": "assistant", "content": reply}]

    def generate_research_reply(
        self,
        chat_history: list[dict[str, str]],
        user_input: str,
        max_new_tokens: int = 200,
        max_sources: int = 3,
    ) -> tuple[str, list[dict[str, str]]]:
        sources = self.research_tools.research(user_input, max_sources=max_sources)
        if not sources:
            reply = (
                "I could not retrieve reliable public sources for that request. "
                "Try making the topic more specific or try again shortly."
            )
            return reply, [
                *chat_history,
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": reply},
            ]

        research_prompt = self._build_research_prompt(user_input, sources)
        model_messages = [*chat_history, {"role": "user", "content": research_prompt}]
        response = _get_pipeline(self.model_id)(
            model_messages,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )
        generated_text = response[0]["generated_text"]
        if isinstance(generated_text, list) and generated_text:
            summary = generated_text[-1].get("content", "").strip()
        else:
            summary = str(generated_text).strip()
        summary = self._strip_generated_sources(summary)

        source_links = "\n".join(
            f"- [{source.title}]({source.url})" for source in sources
        )
        reply = f"{summary}\n\n**Sources**\n{source_links}"
        updated_history = [
            *chat_history,
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": reply},
        ]
        return reply, updated_history

    @staticmethod
    def _strip_generated_sources(summary: str) -> str:
        source_heading = re.compile(
            r"\n\s*(?:#{1,6}\s*)?(?:\*\*)?"
            r"(?:sources?|references?|citations?)(?:\*\*)?\s*:?\s*\n",
            flags=re.IGNORECASE,
        )
        match = source_heading.search(summary)
        return summary[: match.start()].rstrip() if match else summary.strip()

    @staticmethod
    def _build_research_prompt(question: str, sources: list[ResearchSource]) -> str:
        evidence = "\n\n".join(
            f"SOURCE {index}: {source.title}\nURL: {source.url}\n{source.content}"
            for index, source in enumerate(sources, start=1)
        )
        return (
            "Research question:\n"
            f"{question}\n\n"
            "Write a short, factual summary using only the evidence below. "
            "Do not invent facts or URLs. Mention disagreements or uncertainty. "
            "Do not add a sources section because the application adds it.\n\n"
            f"{evidence}"
        )
