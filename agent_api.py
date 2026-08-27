from __future__ import annotations

import os
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from first_agent import ChatMessage, DEFAULT_MODEL_ID, FirstAgent, initial_chat


def _allowed_origins() -> list[str]:
    origins = os.getenv("CORS_ORIGINS")
    if origins:
        return [origin.strip() for origin in origins.split(",") if origin.strip()]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    chat: list[ChatMessage] | None = None
    max_new_tokens: int | None = Field(default=None, ge=1, le=2048)


class ChatResponse(BaseModel):
    reply: str
    chat: list[ChatMessage]
    elapsed_seconds: float
    model_id: str


class HealthResponse(BaseModel):
    status: str
    model_id: str


app = FastAPI(
    title="First Agent API",
    description="HTTP API for the reusable FirstAgent service layer.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

agent = FirstAgent()
agent_lock = Lock()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", model_id=DEFAULT_MODEL_ID)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        current_chat = request.chat or initial_chat()
        with agent_lock:
            result = agent.respond(
                request.message,
                chat=current_chat,
                max_new_tokens=request.max_new_tokens,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    return ChatResponse(
        reply=result.reply,
        chat=result.chat,
        elapsed_seconds=result.elapsed_seconds,
        model_id=agent.model_id,
    )
