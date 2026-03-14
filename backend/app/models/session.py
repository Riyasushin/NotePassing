"""
会话模型 - 存储聊天会话信息
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Session(Base):
    """
    会话表 - 存储用户间的聊天会话
    
    - 临时会话: is_temp=True, 离开范围后过期
    - 永久会话: is_temp=False, 好友间的长期会话
    """
    
    __tablename__ = "sessions"
    
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user1_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user2_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    is_temp: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    expired_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # 唯一约束 - 两个用户间只能有一个会话
    __table_args__ = (
        UniqueConstraint("user1_id", "user2_id", name="uq_session_users"),
    )
    
    # 关系
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="session",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    
    def is_expired(self) -> bool:
        """检查会话是否已过期"""
        if not self.is_temp:
            return False
        if self.expired_at is None:
            return False
        return datetime.utcnow() > self.expired_at
    
    def get_other_user(self, user_id: uuid.UUID) -> uuid.UUID:
        """获取会话中的另一方用户ID"""
        if user_id == self.user1_id:
            return self.user2_id
        return self.user1_id
