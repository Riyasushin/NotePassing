"""Device model."""
from datetime import datetime
from typing import List, Optional, Union

from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class Device(Base):
    """Device model for storing user device information."""
    
    __tablename__ = "devices"
    
    device_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    profile: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    role_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    temp_ids = relationship("TempID", back_populates="device", cascade="all, delete-orphan")
    sent_friend_requests = relationship(
        "Friendship",
        foreign_keys="Friendship.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan"
    )
    received_friend_requests = relationship(
        "Friendship",
        foreign_keys="Friendship.receiver_id",
        back_populates="receiver",
        cascade="all, delete-orphan"
    )
    sent_messages = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan"
    )
    received_messages = relationship(
        "Message",
        foreign_keys="Message.receiver_id",
        back_populates="receiver",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Device(device_id={self.device_id}, nickname={self.nickname})>"
