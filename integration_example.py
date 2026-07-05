"""
Integration Example — Plug-and-Play Usage
==========================================
This demonstrates how GeminiChatbot can be embedded into
ANY existing FastAPI (or other Python) project with only a few lines.

All you need:
  1. Copy the chatbot/ project folder next to your project
  2. Install requirements: pip install -r chatbot/requirements.txt
  3. Import GeminiChatbot from chatbot.chatbot
  4. Call bot.chat() in any route or function

No modifications to the chatbot source code are required.
"""

from fastapi import FastAPI
from pydantic import BaseModel

# ── The only import needed from the chatbot module ──
from chatbot import GeminiChatbot

# Initialize your existing application
app = FastAPI(title="My Existing Application")

# ── Initialize the chatbot (reads GEMINI_API_KEY from .env) ──
bot = GeminiChatbot()

# ── Optionally customize personality per use case ──
# bot = GeminiChatbot(
#     system_prompt="You are a Python expert assistant.",
# )


# ─────────────────────────────────────────────────────
# Example: Attach chatbot to your existing routes
# ─────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    user_id: str = "anonymous"


@app.post("/ask")
def ask(request: AskRequest):
    """
    A simple endpoint showing how to integrate the chatbot.
    The chatbot maintains separate conversation history per user_id.
    """
    answer = bot.chat(
        message=request.question,
        session_id=request.user_id,   # one history per user
    )
    return {"answer": answer}


@app.post("/ask-as-expert")
def ask_expert(request: AskRequest):
    """
    Override the system prompt per-call for different AI personas.
    The core chatbot code doesn't change at all.
    """
    answer = bot.chat(
        message=request.question,
        session_id=f"expert-{request.user_id}",
        system_prompt="You are a senior software architect. Be concise and technical.",
    )
    return {"answer": answer}


@app.post("/reset/{user_id}")
def reset_user_chat(user_id: str):
    """Clear a specific user's conversation history."""
    bot.new_session(session_id=user_id)
    return {"message": f"Chat history cleared for user '{user_id}'"}


@app.get("/chatbot-status")
def chatbot_status():
    """Example: expose chatbot info in your own status endpoint."""
    return {
        "model": bot.current_model,
        "active_sessions": bot.session_count,
    }


# ─────────────────────────────────────────────────────
# Example: Use outside of a web framework (script / CLI)
# ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    # ── Standalone script usage ──
    bot2 = GeminiChatbot()

    print("=== GeminiChatbot Standalone Script ===")
    print("Type 'quit' to exit.\n")

    session = "cli-demo"
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue
        reply = bot2.chat(message=user_input, session_id=session)
        print(f"\nGemini: {reply}\n")

    # ── OR run the integration server ──
    # uvicorn.run(app, host="0.0.0.0", port=9000)
