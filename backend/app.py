from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import database
from analysis_service import ConversationAnalyzer
from rag_service import RagChatService
# from schemas import ChatRequest, ChatResponse, EndSessionRequest, EndSessionResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    print("[APP] database initialized", flush=True)
    yield

class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    need_human: bool = False
    sources: list[str] = Field(default_factory=list)


class EndSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    rating: int = Field(..., ge=1, le=5)


class Insight(BaseModel):
    session_id: str
    category: str
    user_need: str
    sentiment: str
    satisfaction: int
    urgency: str
    summary: str
    hidden_topic: str
    recommended_action: str


class EndSessionResponse(BaseModel):
    success: bool
    analysis: Insight
app = FastAPI(
    title="DataPro Intelligent Chatbot API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_service = RagChatService()
analyzer = ConversationAnalyzer()


@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> dict:
    print(f"[CHAT] session={request.session_id} message={request.message}", flush=True)

    database.ensure_session(request.session_id)
    database.save_message(request.session_id, "user", request.message)

    history = database.get_messages(request.session_id)
    result = rag_service.answer(request.message, history)

    print(
        f"[BOT] need_human={result['need_human']} reply={result['reply'][:100]}",
        flush=True,
    )

    database.save_message(request.session_id, "bot", result["reply"])

    return {
        "session_id": request.session_id,
        "reply": result["reply"],
        "need_human": result["need_human"],
        "sources": result["sources"],
    }


@app.post("/api/end_session", response_model=EndSessionResponse)
def end_session(request: EndSessionRequest) -> dict:
    print(
        f"[END_SESSION] session={request.session_id} rating={request.rating}",
        flush=True,
    )

    database.end_session(request.session_id, request.rating)
    messages = database.get_messages(request.session_id)

    insight = analyzer.analyze(request.session_id, messages, request.rating)
    database.save_insight(insight)

    print(
        f"[INSIGHT] category={insight['category']} sentiment={insight['sentiment']} urgency={insight['urgency']}",
        flush=True,
    )

    return {
        "success": True,
        "analysis": insight,
    }


@app.get("/api/insights")
def get_insights() -> list[dict]:
    print("[INSIGHTS] list requested", flush=True)
    return database.list_insights()
