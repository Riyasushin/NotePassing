"""Presence model for tracking nearby relationships."""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Presence(Base):
    """
    Presence model records when a device detects another device nearby.
    Note: Server does not track online status, only last seen time.
    """
    
    __tablename__ = "presences"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    nearby_device_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    rssi: Mapped[int] = mapped_column(Integer, nullable=False)  # Signal strength
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_boost_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True  # Last time boost was triggered for this pair
    )
    
    __table_args__ = (
        UniqueConstraint('device_id', 'nearby_device_id', name='uix_presence_pair'),
    )
    
    def __repr__(self) -> str:
        return f"<Presence(device_id={self.device_id}, nearby={self.nearby_device_id})>"
