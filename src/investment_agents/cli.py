from __future__ import annotations

import argparse

from investment_agents.agents.orchestrator import OrchestratorAgent
from investment_agents.core.chat import run_cli as run_local_llm_cli
from investment_agents.core.config import get_settings
from investment_agents.core.messages import initial_chat
from investment_agents.tools.registry import ToolRegistry


def run_orchestrator_cli() -> None:
    settings = get_settings()
    registry = ToolRegistry.from_settings(settings)
    orchestrator = OrchestratorAgent.from_tool_registry(registry, model_id=settings.model_id)
    chat = initial_chat()

    print("Investment orchestrator ready. Type a question, or 'quit' to stop.\n")
    print("Tool readiness:")
    for item in registry.readiness_dicts():
        label = "ready" if item["configured"] else "needs configuration"
        print(f"- {item['tool_name']}: {label}")
        if item["missing_settings"]:
            print(f"  missing: {', '.join(item['missing_settings'])}")
    print()

    while True:
        try:
            user_input = input("> ").strip()
            if user_input.lower() in {"quit", "exit"}:
                print("Goodbye!")
                break
            if not user_input:
                continue

            try:
                result = orchestrator.respond(user_input, chat=chat)
            except Exception as exc:
                print(f"Agent error: {exc}")
                continue

            chat = result.chat
            print(f"\nAgent: {result.reply}\n")
            print(f"(Response time: {result.elapsed_seconds:.2f} seconds)\n")

        except KeyboardInterrupt:
            print("\n(Stopped) Goodbye!")
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the investment agent CLI.")
    parser.add_argument(
        "--local-llm",
        action="store_true",
        help="Run the legacy local Hugging Face chat wrapper instead of the investment orchestrator.",
    )
    args = parser.parse_args()
    if args.local_llm:
        run_local_llm_cli()
        return
    run_orchestrator_cli()


if __name__ == "__main__":
    main()
