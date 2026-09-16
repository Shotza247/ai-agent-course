from ..tools import ResearchSource


def build_research_prompt(question: str, sources: list[ResearchSource]) -> str:
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
