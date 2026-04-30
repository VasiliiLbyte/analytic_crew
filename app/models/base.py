from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    subscription_plan: Mapped[str] = mapped_column(Text, nullable=False, server_default="free")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    workspaces: Mapped[list[Workspace]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    feedback_items: Mapped[list[HumanFeedback]] = relationship(back_populates="user")


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped[User | None] = relationship(back_populates="workspaces")
    cycles: Mapped[list[Cycle]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class Cycle(Base):
    __tablename__ = "cycles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True
    )
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="running")
    current_phase: Mapped[str] = mapped_column(Text, nullable=False, server_default="scout")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    workspace: Mapped[Workspace | None] = relationship(back_populates="cycles")
    signals: Mapped[list[Signal]] = relationship(back_populates="cycle", cascade="all, delete-orphan")
    trends: Mapped[list[Trend]] = relationship(back_populates="cycle", cascade="all, delete-orphan")
    ideas: Mapped[list[Idea]] = relationship(back_populates="cycle", cascade="all, delete-orphan")
    agent_logs: Mapped[list[AgentLog]] = relationship(
        back_populates="cycle", cascade="all, delete-orphan"
    )


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    cycle_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cycles.id", ondelete="CASCADE"), nullable=True
    )
    source_url: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(Text)
    content_snippet: Mapped[str | None] = mapped_column(Text)
    raw_data_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    cycle: Mapped[Cycle | None] = relationship(back_populates="signals")


class Trend(Base):
    __tablename__ = "trends"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    cycle_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cycles.id", ondelete="CASCADE"), nullable=True
    )
    trend_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    velocity_score: Mapped[float | None] = mapped_column(Float)
    related_signals: Mapped[list[UUID] | None] = mapped_column(ARRAY(PGUUID(as_uuid=True)))
    metadata_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    cycle: Mapped[Cycle | None] = relationship(back_populates="trends")


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    cycle_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cycles.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    problem: Mapped[str | None] = mapped_column(Text)
    solution: Mapped[str | None] = mapped_column(Text)
    market_analysis_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    critic_score: Mapped[float | None] = mapped_column(Float)
    critic_comment: Mapped[str | None] = mapped_column(Text)
    validation_status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    gtm_plan_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    sources_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    cycle: Mapped[Cycle | None] = relationship(back_populates="ideas")
    feedback_items: Mapped[list[HumanFeedback]] = relationship(
        back_populates="idea", cascade="all, delete-orphan"
    )


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    cycle_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cycles.id", ondelete="CASCADE"), nullable=True
    )
    agent_name: Mapped[str] = mapped_column(Text, nullable=False)
    input_state_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    output_state_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    log_message: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    cycle: Mapped[Cycle | None] = relationship(back_populates="agent_logs")


class HumanFeedback(Base):
    __tablename__ = "human_feedback"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    idea_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ideas.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    feedback_type: Mapped[str] = mapped_column(String, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    idea: Mapped[Idea | None] = relationship(back_populates="feedback_items")
    user: Mapped[User | None] = relationship(back_populates="feedback_items")


class LLMCache(Base):
    __tablename__ = "llm_cache"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    prompt_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    response_json: Mapped[dict[str, Any] | list[Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
