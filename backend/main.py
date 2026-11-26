
import os
import time
from collections import defaultdict, deque
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# --------------------------------------------------
# J-SPARK AI 2.0 — GEMINI BACKEND
# --------------------------------------------------

APP_NAME = "J-SPARK AI"
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
API_KEY = os.getenv("GEMINI_API_KEY")

app = FastAPI(
    title="J-SPARK AI API",
    description="The secure AI backend for J-SPARK AI.",
    version="2.0.0"
)

# Only allow requests from the published J-SPARK website
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jmv172.github.io",
        "http://localhost:3000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"]
)

# Basic per-instance request limit.
# Production deployment needs stronger shared rate limiting.
request_history = defaultdict(deque)
MAX_REQUESTS_PER_MINUTE = 15


class ChatMessage(BaseModel):
    role: Literal["user", "model"]
    content: str = Field(min_length=1, max_length=6000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    language: str = Field(default="English", max_length=40)
    mode: str = Field(default="chat", max_length=30)


def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    history = request_history[ip]

    while history and now - history[0] > 60:
        history.popleft()

    if len(history) >= MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a minute."
        )

    history.append(now)


@app.get("/")
def home():
    return {
        "name": APP_NAME,
        "version": "2.0.0",
        "status": "online",
        "message": "Welcome to the J-SPARK AI backend."
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "gemini_configured": bool(API_KEY),
        "model": MODEL_NAME
    }


@app.post("/chat")
def chat(data: ChatRequest, request: Request):
    check_rate_limit(request)

    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="The AI service is not configured yet."
        )

    if data.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="The final message must be from the user."
        )

    system_instruction = f"""
You are J-SPARK AI, a helpful, knowledgeable and friendly AI assistant.

Your motto is: INTELLIGENCE WITHOUT BORDERS.

You can help with:
- Education and explanations
- Programming and technology
- Research and learning
- Writing and creativity
- Problem solving
- General questions

The selected language is {data.language}.
Respond in that language whenever practical.

The selected workspace is {data.mode}.
Adapt your assistance to that workspace.

Be accurate. If you are uncertain, say so.
Do not invent facts or pretend to have performed actions.
Keep interactions age-appropriate, respectful and educational.
Never simulate a romantic relationship with the user.
Do not provide instructions that facilitate dangerous real-world activities.
"""

    contents = []

    for message in data.messages:
        contents.append(
            types.Content(
                role=message.role,
                parts=[
                    types.Part.from_text(text=message.content)
                ]
            )
        )

    try:
        client = genai.Client(api_key=API_KEY)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                max_output_tokens=1500
            )
        )

        answer = response.text

        if not answer:
            raise HTTPException(
                status_code=502,
                detail="The AI did not return a text response."
            )

        return {
            "success": True,
            "assistant": "J-SPARK AI",
            "model": MODEL_NAME,
            "reply": answer
        }

    except HTTPException:
        raise

    except Exception:
        # Do not expose API credentials or internal error details.
        raise HTTPException(
            status_code=502,
            detail="Gemini could not complete the request. Please try again."
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000"))
    )
