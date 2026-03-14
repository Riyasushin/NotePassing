"""
附近关系模型 - 记录用户之间的附近发现关系
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Presence(Base):
    """
    附近关系表 - 记录谁在谁附近
    
    V2 重要变更: 不维护在线状态，只记录最后发现时间
    """
    
    __tablename__ = "presence"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False
    )
    nearby_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    last_disconnect_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    last_boost_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # 复合主键
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "nearby_user_id"),
    )
    
    # 关系
    user: Mapped["Device"] = relationship(
        "Device",
        foreign_keys=[user_id],
        lazy="joined"
    )
    nearby_user: Mapped["Device"] = relationship(
        "Device",
        foreign_keys=[nearby_user_id],
        lazy="joined"
    )
    
    def can_trigger_boost(self, cooldown_minutes: int = 5) -> bool:
        """检查是否可以触发Boost（冷却期检查）"""
        if self.last_boost_at is None:
            return True
        from datetime import timedelta
        cooldown = timedelta(minutes=cooldown_minutes)
        return datetime.utcnow() - self.last_boost_at > cooldown
