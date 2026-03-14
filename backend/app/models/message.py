"""
消息模型 - 存储聊天消息
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    """
    消息表 - 存储聊天消息
    
    消息类型:
    - common: 普通文本消息
    - heartbeat: 心跳消息（附近存在感通知）
    
    消息状态:
    - sent: 已发送
    - read: 已读
    """
    
    __tablename__ = "messages"
    
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    receiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="common", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="sent", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # 关系
    session: Mapped["Session"] = relationship("Session", back_populates="messages")
    sender: Mapped["Device"] = relationship(
        "Device",
        foreign_keys=[sender_id],
        lazy="joined"
    )
    receiver: Mapped["Device"] = relationship(
        "Device",
        foreign_keys=[receiver_id],
        lazy="joined"
    )
    
    def mark_as_read(self) -> None:
        """标记消息为已读"""
        if self.status != "read":
            self.status = "read"
            self.read_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "message_id": str(self.message_id),
            "sender_id": str(self.sender_id),
            "content": self.content,
            "type": self.type,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
