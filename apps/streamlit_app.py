import sys
import re
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.first_agent.agent import DEFAULT_MODEL_ID, DEFAULT_SYSTEM_PROMPT, LocalChatAgent

SOURCE_SEPARATOR = "\n\n**Sources**\n"


st.set_page_config(
    page_title="First Research Agent",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main .block-container {
        max-width: 960px;
        padding-top: 2rem;
    }
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(49, 51, 63, 0.15);
    }
    .agent-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .agent-subtitle {
        color: rgba(49, 51, 63, 0.7);
        margin-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_agent(model_id: str, system_prompt: str) -> LocalChatAgent:
    return LocalChatAgent(model_id=model_id, system_prompt=system_prompt)


def reset_chat(system_prompt: str) -> None:
    st.session_state.messages = [{"role": "system", "content": system_prompt}]


def render_message(content: str) -> None:
    answer, separator, sources = content.partition(SOURCE_SEPARATOR)
    duplicate_sources = re.search(
        r"\n\s*(?:#{1,6}\s*)?(?:\*\*)?"
        r"(?:sources?|references?|citations?)(?:\*\*)?\s*:?\s*\n",
        answer,
        flags=re.IGNORECASE,
    )
    if duplicate_sources:
        answer = answer[: duplicate_sources.start()].rstrip()
    st.markdown(answer)
    if separator and sources:
        with st.expander("Sources", expanded=False):
            st.markdown(sources)


with st.sidebar:
    st.header("Settings")
    model_id = st.text_input("Model", value=DEFAULT_MODEL_ID)
    system_prompt = st.text_area("System prompt", value=DEFAULT_SYSTEM_PROMPT, height=120)
    max_new_tokens = st.slider("Max response tokens", min_value=32, max_value=512, value=200, step=32)
    max_sources = st.slider("Sources per answer", min_value=1, max_value=5, value=3)

    if st.button("Reset chat", width="stretch", icon=":material/refresh:"):
        reset_chat(system_prompt)

    st.divider()
    st.caption("Research uses keyless web search and public webpages. The first answer may take a while.")


if "messages" not in st.session_state:
    reset_chat(system_prompt)

if st.session_state.messages and st.session_state.messages[0]["content"] != system_prompt:
    reset_chat(system_prompt)

st.markdown('<div class="agent-title">First Research Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="agent-subtitle">Search the web and receive a concise, source-linked summary.</div>',
    unsafe_allow_html=True,
)

for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        render_message(message["content"])

prompt = st.chat_input("What would you like to research?", submit_mode="disable")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    agent = get_agent(model_id=model_id, system_prompt=system_prompt)
    with st.chat_message("assistant"):
        with st.spinner("Searching, reading, and summarizing..."):
            try:
                reply, updated_messages = agent.generate_research_reply(
                    chat_history=st.session_state.messages,
                    user_input=prompt,
                    max_new_tokens=max_new_tokens,
                    max_sources=max_sources,
                )
                st.session_state.messages = updated_messages
                render_message(reply)
            except Exception as exc:
                st.error(f"Agent error: {exc}")
