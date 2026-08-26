import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    auth_tokens: Mapped[list["AuthToken"]] = relationship(back_populates="candidate")
    interviews: Mapped[list["Interview"]] = relationship(back_populates="candidate")


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="auth_tokens")

    __table_args__ = (Index("ix_auth_tokens_token_hash", "token_hash"),)


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    current_question_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_question_topic: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    current_question_difficulty: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    current_question_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    questions_answered: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="interviews")
    turns: Mapped[list["InterviewTurn"]] = relationship(back_populates="interview")
    report: Mapped["InterviewReport | None"] = relationship(back_populates="interview")

    __table_args__ = (
        Index(
            "uq_interviews_candidate_active",
            "candidate_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )


class InterviewTurn(Base):
    __tablename__ = "interview_turns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interviews.id"), nullable=False
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_id: Mapped[str] = mapped_column(String(64), nullable=False)
    question_topic: Mapped[str] = mapped_column(String(128), nullable=False)
    question_difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    question_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_score: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluation_feedback: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluation_model: Mapped[str] = mapped_column(String(128), nullable=False)
    evaluation_raw_response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    interview: Mapped["Interview"] = relationship(back_populates="turns")

    __table_args__ = (
        UniqueConstraint(
            "interview_id", "turn_number", name="uq_interview_turn_number"
        ),
    )


class InterviewReport(Base):
    __tablename__ = "interview_reports"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interviews.id"), primary_key=True
    )
    overall_summary: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[list] = mapped_column(JSONB, nullable=False)
    weaknesses: Mapped[list] = mapped_column(JSONB, nullable=False)
    suggestions: Mapped[list] = mapped_column(JSONB, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    interview: Mapped["Interview"] = relationship(back_populates="report")
