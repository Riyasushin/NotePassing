"""Friendship model."""
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Friendship(Base):
    """
    Friendship relationship between two devices.
    Status: pending, accepted, rejected
    """
    
    __tablename__ = "friendships"
    
    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sender_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    receiver_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, accepted, rejected
    message: Mapped[str | None] = mapped_column(String(200), nullable=True)  # Request message
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    sender = relationship("Device", foreign_keys=[sender_id], back_populates="sent_friend_requests")
    receiver = relationship("Device", foreign_keys=[receiver_id], back_populates="received_friend_requests")
    
    __table_args__ = (
        Index('ix_friendships_sender', 'sender_id'),
        Index('ix_friendships_receiver', 'receiver_id'),
        Index('ix_friendships_status', 'status'),
    )
    
    def __repr__(self) -> str:
        return f"<Friendship(request_id={self.request_id}, status={self.status})>"
