import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.first_agent.agent import DEFAULT_MODEL_ID, DEFAULT_SYSTEM_PROMPT, LocalChatAgent


st.set_page_config(
    page_title="First Agent",
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


with st.sidebar:
    st.header("Settings")
    model_id = st.text_input("Model", value=DEFAULT_MODEL_ID)
    system_prompt = st.text_area("System prompt", value=DEFAULT_SYSTEM_PROMPT, height=120)
    max_new_tokens = st.slider("Max response tokens", min_value=32, max_value=512, value=200, step=32)

    if st.button("Reset chat", use_container_width=True):
        reset_chat(system_prompt)

    st.divider()
    st.caption("The first response can take a while while the model loads or downloads.")


if "messages" not in st.session_state:
    reset_chat(system_prompt)

if st.session_state.messages and st.session_state.messages[0]["content"] != system_prompt:
    reset_chat(system_prompt)

st.markdown('<div class="agent-title">First Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="agent-subtitle">Chat with your local Hugging Face text-generation agent.</div>',
    unsafe_allow_html=True,
)

for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask the agent something")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    agent = get_agent(model_id=model_id, system_prompt=system_prompt)
    with st.chat_message("assistant"):
        with st.spinner("Generating response..."):
            try:
                reply, updated_messages = agent.generate_reply(
                    chat_history=st.session_state.messages,
                    user_input=prompt,
                    max_new_tokens=max_new_tokens,
                )
                st.session_state.messages = updated_messages
                st.markdown(reply)
            except Exception as exc:
                st.error(f"Agent error: {exc}")
