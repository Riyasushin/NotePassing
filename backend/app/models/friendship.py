"""
好友关系模型 - 存储好友申请和关系状态
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Friendship(Base):
    """
    好友关系表 - 存储好友申请和关系
    
    状态说明:
    - pending: 待处理
    - accepted: 已接受
    - rejected: 已拒绝
    
    拒绝后24小时内不能再次申请（冷却期）
    """
    
    __tablename__ = "friendships"
    
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    friend_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # 唯一约束 - 同一方向只能有一个关系记录
    __table_args__ = (
        UniqueConstraint("user_id", "friend_id", name="uq_friendship"),
    )
    
    # 关系
    user: Mapped["Device"] = relationship(
        "Device",
        foreign_keys=[user_id],
        back_populates="sent_friendships",
        lazy="joined"
    )
    friend: Mapped["Device"] = relationship(
        "Device",
        foreign_keys=[friend_id],
        back_populates="received_friendships",
        lazy="joined"
    )
    
    def is_in_cooldown(self, hours: int = 24) -> bool:
        """检查是否在冷却期内"""
        if self.status != "rejected":
            return False
        from datetime import timedelta
        cooldown = timedelta(hours=hours)
        return datetime.utcnow() - self.updated_at < cooldown
