"""Block model for user blocking relationships."""
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Block(Base):
    """
    Block relationship - when a device blocks another device.
    After blocking, neither can see each other.
    """
    
    __tablename__ = "blocks"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('device_id', 'target_id', name='uix_block_pair'),
        Index('ix_blocks_device', 'device_id'),
        Index('ix_blocks_target', 'target_id'),
    )
    
    def __repr__(self) -> str:
        return f"<Block(device_id={self.device_id}, target={self.target_id})>"
