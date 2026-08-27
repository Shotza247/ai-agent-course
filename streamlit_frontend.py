from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

from first_agent import DEFAULT_MODEL_ID, initial_chat

DEFAULT_API_URL = os.getenv("AGENT_API_URL", "http://localhost:8000")


def _api_url() -> str:
    return st.session_state.api_url.rstrip("/")


def check_api_health(api_url: str) -> dict[str, Any]:
    response = requests.get(f"{api_url.rstrip('/')}/health", timeout=5)
    response.raise_for_status()
    return response.json()


def send_message(api_url: str, message: str) -> dict[str, Any]:
    response = requests.post(
        f"{api_url.rstrip('/')}/chat",
        json={"message": message, "chat": st.session_state.chat},
        timeout=240,
    )
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="First Agent", layout="wide")
st.title("First Agent")

st.session_state.setdefault("chat", initial_chat())
st.session_state.setdefault("api_url", DEFAULT_API_URL)

with st.sidebar:
    st.text_input("Agent API URL", key="api_url")

    if st.button(":material/network_ping: Check status"):
        try:
            health = check_api_health(_api_url())
            st.success(f"{health['status']} - {health['model_id']}")
        except requests.RequestException as exc:
            st.error(f"API unavailable: {exc}")

    if st.button(":material/delete: Clear conversation"):
        st.session_state.chat = initial_chat()
        st.rerun()

    st.caption(f"Default model: {DEFAULT_MODEL_ID}")

for message in st.session_state.chat:
    role = message.get("role")
    if role not in {"user", "assistant"}:
        continue

    with st.chat_message(role):
        st.write(message.get("content", ""))

if prompt := st.chat_input("Message the agent"):
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = send_message(_api_url(), prompt)
                st.session_state.chat = result["chat"]
                st.write(result["reply"])
                st.caption(f"{result['elapsed_seconds']:.2f}s via FastAPI")
            except requests.RequestException as exc:
                st.session_state.chat = [
                    *st.session_state.chat,
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": f"API error: {exc}"},
                ]
                st.error(f"API error: {exc}")
