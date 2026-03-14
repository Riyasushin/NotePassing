"""Temp ID model."""
from datetime import datetime, timedelta

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TempID(Base):
    """Temporary ID model for BLE broadcast."""
    
    __tablename__ = "temp_ids"
    
    temp_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    device_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=10)
    )
    
    # Relationships
    device = relationship("Device", back_populates="temp_ids")
    
    def __repr__(self) -> str:
        return f"<TempID(temp_id={self.temp_id}, device_id={self.device_id})>"
    
    def is_expired(self) -> bool:
        """Check if this temp ID has expired."""
        return datetime.utcnow() > self.expires_at
