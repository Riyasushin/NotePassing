"""Message model."""
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    """Chat message model."""
    
    __tablename__ = "messages"
    
    message_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    receiver_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="common")  # common, heartbeat
    status: Mapped[str] = mapped_column(String(20), default="sent")  # sent, delivered, read
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    session = relationship("Session", back_populates="messages")
    sender = relationship("Device", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("Device", foreign_keys=[receiver_id], back_populates="received_messages")
    
    __table_args__ = (
        Index('ix_messages_session', 'session_id'),
        Index('ix_messages_sender', 'sender_id'),
        Index('ix_messages_receiver', 'receiver_id'),
        Index('ix_messages_created', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<Message(message_id={self.message_id}, type={self.type})>"
