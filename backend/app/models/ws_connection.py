"""WebSocket connection model for tracking active connections."""
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WebSocketConnection(Base):
    """
    WebSocket connection tracking.
    Note: This is for connection management only, not for online status.
    """
    
    __tablename__ = "websocket_connections"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    connection_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_ping_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    __table_args__ = (
        Index('ix_ws_connections_device', 'device_id'),
        Index('ix_ws_connections_id', 'connection_id'),
    )
    
    def __repr__(self) -> str:
        return f"<WebSocketConnection(device_id={self.device_id}, conn_id={self.connection_id})>"
