"""
屏蔽关系模型 - 存储用户间的屏蔽关系
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Block(Base):
    """
    屏蔽表 - 存储屏蔽关系
    
    屏蔽效果:
    - 双方互不可见（附近列表）
    - 消息不可达
    - 好友申请不可发送
    - 如存在好友关系，自动删除
    """
    
    __tablename__ = "blocks"
    
    blocker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    
    # 复合主键
    __table_args__ = (
        PrimaryKeyConstraint("blocker_id", "target_id"),
    )
    
    # 关系
    blocker: Mapped["Device"] = relationship(
        "Device",
        foreign_keys=[blocker_id],
        lazy="joined"
    )
    target: Mapped["Device"] = relationship(
        "Device",
        foreign_keys=[target_id],
        lazy="joined"
    )
