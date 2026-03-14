"""Session model for chat sessions."""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Session(Base):
    """
    Chat session between two devices.
    - is_temp=True: Temporary session for non-friends
    - is_temp=False: Permanent session for friends
    """
    
    __tablename__ = "sessions"
    
    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_a_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    device_b_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    is_temp: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, expired
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True  # For temp sessions
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_sessions_device_a', 'device_a_id'),
        Index('ix_sessions_device_b', 'device_b_id'),
        Index('ix_sessions_pair', 'device_a_id', 'device_b_id'),
    )
    
    def __repr__(self) -> str:
        return f"<Session(session_id={self.session_id}, is_temp={self.is_temp})>"
    
    def is_expired(self) -> bool:
        """Check if this session has expired."""
        if not self.is_temp or not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def get_peer_id(self, device_id: str) -> str:
        """Get the peer device ID given one device ID."""
        return self.device_b_id if device_id == self.device_a_id else self.device_a_id
