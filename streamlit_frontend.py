import os
from dotenv import load_dotenv
from huggingface_hub import login
from transformers import pipeline
import streamlit as st

# Load environment and optional HF token
load_dotenv()
hf_token = os.getenv("HF_TOKEN")
if hf_token:
    try:
        login(token=hf_token)
    except Exception as e:
        st.warning(f"HF login failed: {e}")

# Friendly check for torchvision — Streamlit shows a warning and stops so the user
# sees a clear action to fix the missing dependency.
try:
    import torchvision  # noqa: F401
except Exception:
    st.warning("Missing dependency 'torchvision'. Install it with:\n  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu\nOr see https://pytorch.org/get-started/locally/ for platform-specific instructions.")
    st.stop()

MODEL_ID = "HuggingFaceTB/SmolLM2-360M-Instruct"

@st.cache_resource
def get_pipeline():
    """Create and cache the transformers pipeline so model is loaded just once."""
    return pipeline(task="text-generation", model=MODEL_ID, dtype="auto")

st.set_page_config(page_title="First Agent (Streamlit)", layout="wide")
st.title("First Agent — Streamlit frontend")
st.markdown("A simple Streamlit UI for interacting with the `first_agent.py` text-generation agent.")

# Initialize session state for chat history
if "chat" not in st.session_state:
    st.session_state.chat = [{"role": "system", "content": "You are a helpful, concise assistant."}]

col1, col2 = st.columns([3, 1])

# Handler that will be run as the button callback. Using on_click avoids modifying
# widget-bound session_state keys after widget instantiation (which raises StreamlitAPIException).
def handle_send():
    user_text = st.session_state.get("user_input", "").strip()
    if not user_text:
        # Nothing to do
        return

    # Append user message to chat
    chat = st.session_state.get("chat", [])
    chat.append({"role": "user", "content": user_text})
    st.session_state.chat = chat

    # Call the model
    pipe = get_pipeline()
    try:
        response = pipe(st.session_state.chat, max_new_tokens=200)
    except Exception as e:
        # Store an assistant message describing the error for visibility
        err_msg = f"Model error: {e}"
        st.session_state.chat.append({"role": "assistant", "content": err_msg})
        # Clear input
        st.session_state.user_input = ""
        return

    # Robustly parse the pipeline response and update chat
    try:
        first = response[0] if isinstance(response, list) else response
        gen = None
        if isinstance(first, dict):
            gen = first.get("generated_text") or first.get("text") or first.get("summary_text")
        else:
            gen = first

        if isinstance(gen, list):
            # full chat history returned — keep it as-is without duplicating the last reply
            st.session_state.chat = gen
        elif isinstance(gen, str):
            st.session_state.chat.append({"role": "assistant", "content": gen})
        else:
            st.session_state.chat.append({"role": "assistant", "content": str(gen)})
    except Exception as e:
        st.session_state.chat.append({"role": "assistant", "content": f"(Could not parse model response: {e})"})

    # Clear the input so the widget becomes empty on next render
    st.session_state.user_input = ""

with col1:
    # The text area creates the widget and binds to st.session_state['user_input']
    st.text_area("Your message", height=120, key="user_input")
    st.button("Send", on_click=handle_send)

with col2:
    if st.button("Clear conversation"):
        st.session_state.chat = [{"role": "system", "content": "You are a helpful, concise assistant."}]
        st.experimental_rerun()

# Show the chat history
st.subheader("Conversation")
for msg in st.session_state.chat:
    role = msg.get("role")
    content = msg.get("content")
    if role == "system":
        st.markdown(f"**System:** {content}")
    elif role == "user":
        st.markdown(f"**You:** {content}")
    elif role == "assistant":
        st.markdown(f"**Assistant:** {content}")
    else:
        # Unknown role — print generically
        st.markdown(f"**{role}:** {content}")

st.markdown("---")
st.caption("Model: %s — uses the same model and behavior as first_agent.py" % MODEL_ID)

st.markdown("Run this app with: `streamlit run streamlit_frontend.py`")