"""
临时ID模型 - 用于BLE广播的临时身份标识
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TempId(Base):
    """
    临时ID表 - 存储设备生成的临时ID
    
    临时ID用于BLE广播，每5分钟轮换一次
    过期后保留5分钟缓冲期用于解析
    """
    
    __tablename__ = "temp_ids"
    
    temp_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # 关系
    device: Mapped["Device"] = relationship("Device", lazy="joined")
    
    def is_expired(self) -> bool:
        """检查是否已过期（包括5分钟缓冲期）"""
        from datetime import timedelta
        buffer_expires = self.expires_at + timedelta(minutes=5)
        return datetime.utcnow() > buffer_expires
    
    def is_active(self) -> bool:
        """检查是否在有效期内（不含缓冲期）"""
        return datetime.utcnow() < self.expires_at
