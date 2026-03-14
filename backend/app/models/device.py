"""
设备模型 - 存储用户设备信息
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Boolean, DateTime, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Device(Base):
    """
    设备表 - 存储用户设备信息
    
    字段说明:
    - device_id: 主键，UUID v4 格式
    - nickname: 昵称，最大50字符
    - avatar: 头像URL
    - tags: 标签列表
    - profile: 个人简介
    - is_anonymous: 是否匿名模式
    - role_name: 匿名角色名
    """
    
    __tablename__ = "devices"
    
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tags: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    profile: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # 关系定义
    sent_friendships = relationship(
        "Friendship", 
        foreign_keys="Friendship.user_id",
        back_populates="user"
    )
    received_friendships = relationship(
        "Friendship",
        foreign_keys="Friendship.friend_id", 
        back_populates="friend"
    )
    
    def to_dict(self, include_private: bool = True) -> dict:
        """转换为字典"""
        data = {
            "device_id": str(self.device_id),
            "nickname": self.nickname,
            "tags": self.tags or [],
            "profile": self.profile,
            "is_anonymous": self.is_anonymous,
            "role_name": self.role_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_private:
            data["avatar"] = self.avatar
        return data
