from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from kevin.api.v1.dependencies import get_current_user
from kevin.database import get_session
from kevin.models.user import User
from kevin.services.gemini import GeminiError, GeminiService

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    year: int | None = None
    month: int | None = None


class ActionResult(BaseModel):
    action: str
    success: bool
    detail: str


class ChatResponse(BaseModel):
    message: str
    actions: list[ActionResult] = []


@router.post("/", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now()
    year = body.year or now.year
    month = body.month or now.month

    try:
        service = GeminiService(
            session=session, user_id=current_user.id, year=year, month=month
        )
        response_text, actions = service.chat(body.message, body.history)
    except GeminiError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    return ChatResponse(
        message=response_text,
        actions=[
            ActionResult(action=a["action"], success=a["success"], detail=a["detail"])
            for a in actions
        ],
    )
