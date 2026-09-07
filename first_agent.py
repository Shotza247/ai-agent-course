from src.first_agent.agent import LocalChatAgent


def main() -> None:
    agent = LocalChatAgent()
    chat = agent.new_chat()

    print(f"Loading {agent.model_id} on first question...")
    print("Agent ready! Type a question, or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("> ").strip()
            if user_input.lower() in {"quit", "exit"}:
                print("Goodbye!")
                break
            if not user_input:
                continue

            reply, chat = agent.generate_research_reply(
                chat_history=chat,
                user_input=user_input,
                max_new_tokens=200,
            )
            print(f"\nAgent: {reply}\n")

        except KeyboardInterrupt:
            print("\n(Stopped) Goodbye!")
            break


if __name__ == "__main__":
    main()
