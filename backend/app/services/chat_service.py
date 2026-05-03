"""
Chat Service
------------
Business logic for multi-turn chat sessions.

Responsibilities:
  - Create / delete sessions
  - Persist user + assistant messages
  - Assemble full history and dispatch to RAG conversation
  - Update session title from first user message
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ChatMessage, ChatSession
from app.schemas import (
    MessageResponse,
    SessionResponse,
    SessionSummary,
)
from app.services.rag_conversation import rag_chat


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def create_session(db: Session, title: str | None = None) -> SessionResponse:
    session = ChatSession(title=title or "New Chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionResponse.model_validate(session)


def delete_session(db: Session, session_id: str) -> bool:
    session = db.get(ChatSession, session_id)
    if not session:
        return False
    db.delete(session)
    db.commit()
    return True


def get_session(db: Session, session_id: str) -> ChatSession | None:
    return db.get(ChatSession, session_id)


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------

def get_messages(db: Session, session_id: str) -> list[MessageResponse]:
    msgs = (
        db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        .scalars()
        .all()
    )
    return [_msg_to_schema(m) for m in msgs]


def _msg_to_schema(m: ChatMessage) -> MessageResponse:
    meta: dict[str, Any] | None = None
    if m.meta:
        try:
            meta = json.loads(m.meta)
        except Exception:
            meta = None
    return MessageResponse(
        id=m.id,
        session_id=m.session_id,
        role=m.role,
        content=m.content,
        meta=meta,
        created_at=m.created_at,
    )


def _build_history(db: Session, session_id: str) -> list[dict[str, str]]:
    """Return all messages as [{"role": ..., "content": ...}, ...] for RAG."""
    msgs = (
        db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        .scalars()
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in msgs]


# ---------------------------------------------------------------------------
# Core: send a user message and get an assistant reply
# ---------------------------------------------------------------------------

async def handle_user_message(
    db: Session,
    session_id: str,
    content: str,
    pipeline: Any | None,
) -> tuple[MessageResponse, MessageResponse]:
    """
    1. Persist the user message.
    2. Fetch full history (including the new message).
    3. Call rag_chat for an assistant response.
    4. Persist the assistant message.
    5. Update session title if this is the first message.
    Returns (user_message_schema, assistant_message_schema).
    """
    session = db.get(ChatSession, session_id)
    if not session:
        raise ValueError(f"Session {session_id!r} not found")

    # 1. Persist user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=content,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 2. Build history (all messages, RAG will use prior context)
    history = _build_history(db, session_id)
    # history already includes the message we just added
    prior_history = history[:-1]  # everything before the latest user turn

    # 3. Get assistant response
    if pipeline is None:
        response_text = f"(Mock) You said: {content}"
        meta = {"mode": "mock"}
        
    else:
        response_text, meta = await rag_chat(
            messages=prior_history,
            query=content,
            pipeline=pipeline,
        )
    # 4. Persist assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=response_text,
        meta=json.dumps(meta) if meta else None,
    )
    db.add(assistant_msg)

    # 5. Update session title from first user message
    if session.title == "New Chat":
        session.title = content[:60] + ("…" if len(content) > 60 else "")

    db.commit()
    db.refresh(assistant_msg)
    db.refresh(session)

    return _msg_to_schema(user_msg), _msg_to_schema(assistant_msg)


# ---------------------------------------------------------------------------
# History / sidebar
# ---------------------------------------------------------------------------

def list_sessions(
    db: Session,
    limit: int = 30,
    offset: int = 0,
) -> tuple[list[SessionSummary], int]:
    """Return recent sessions ordered by last-updated desc, with preview."""
    total: int = db.execute(select(func.count()).select_from(ChatSession)).scalar_one()

    sessions = (
        db.execute(
            select(ChatSession)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )

    summaries: list[SessionSummary] = []
    for s in sessions:
        # Get last message preview
        last_msg = (
            db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == s.id)
                .order_by(ChatMessage.created_at.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        msg_count: int = db.execute(
            select(func.count()).select_from(ChatMessage).where(
                ChatMessage.session_id == s.id
            )
        ).scalar_one()

        preview = None
        if last_msg:
            preview = last_msg.content[:80] + ("…" if len(last_msg.content) > 80 else "")

        summaries.append(
            SessionSummary(
                id=s.id,
                title=s.title,
                last_message_preview=preview,
                message_count=msg_count,
                updated_at=s.updated_at,
            )
        )

    return summaries, total
