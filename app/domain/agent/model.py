from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.persistence import Base, BaseEntity


class QTableEntry(BaseEntity):
    __tablename__ = "q_table_entries"
    __table_args__ = (UniqueConstraint("user_id", "domain", "state", "action"),)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    domain: Mapped[str] = mapped_column(
        Enum("pitch", "rhythm", "posture", name="agent_domain")
    )
    state: Mapped[str] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(40))
    q_value: Mapped[float] = mapped_column(Float, server_default=text("0"))
    update_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"
    __table_args__ = (
        Index("ix_feedback_events_session_measure", "session_id", "measure_index"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sessions.id"))
    measure_index: Mapped[int] = mapped_column(Integer)
    domain: Mapped[str] = mapped_column(
        Enum("pitch", "rhythm", "posture", name="agent_domain")
    )
    state: Mapped[str] = mapped_column(String(30))
    action_id: Mapped[str] = mapped_column(String(10))
    action: Mapped[str] = mapped_column(String(40))
    feedback: Mapped[str] = mapped_column(Text)
    reward: Mapped[float | None] = mapped_column(Float, nullable=True)
    q: Mapped[float] = mapped_column(Float)
    cause_domain: Mapped[str | None] = mapped_column(String(10), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
