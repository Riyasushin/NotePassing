from __future__ import annotations

from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import MetaData, case, func, literal, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    np_site_database_url: str | None = None
    database_url: str | None = None
    np_site_refresh_seconds: int = 5
    np_site_presence_seconds: int = 180
    np_site_message_minutes: int = 15
    np_site_max_nodes: int = 80
    app_name: str = "NotePassing Network Site"

    @property
    def resolved_database_url(self) -> str:
        url = self.np_site_database_url or self.database_url
        if not url:
            raise RuntimeError("DATABASE_URL or NP_SITE_DATABASE_URL is required")
        return url


settings = Settings()
metadata = MetaData()


@dataclass
class AppState:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]


async def build_payload(session: AsyncSession) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    presence_cutoff = now - timedelta(seconds=settings.np_site_presence_seconds)
    message_cutoff = now - timedelta(minutes=settings.np_site_message_minutes)

    devices = metadata.tables["devices"]
    temp_ids = metadata.tables["temp_ids"]
    presences = metadata.tables["presences"]
    friendships = metadata.tables["friendships"]
    sessions = metadata.tables["sessions"]
    messages = metadata.tables["messages"]

    broadcasting_ids = {
        row[0]
        for row in (
            await session.execute(
                select(temp_ids.c.device_id).where(temp_ids.c.expires_at > now).distinct()
            )
        ).all()
    }

    recent_presence_rows = (
        await session.execute(
            select(
                presences.c.device_id,
                presences.c.nearby_device_id,
                presences.c.rssi,
                presences.c.last_seen_at,
            ).where(presences.c.last_seen_at >= presence_cutoff)
        )
    ).all()

    recent_message_rows = (
        await session.execute(
            select(
                messages.c.sender_id,
                messages.c.receiver_id,
                messages.c.created_at,
            ).where(messages.c.created_at >= message_cutoff)
        )
    ).all()

    friendship_rows = (
        await session.execute(
            select(
                friendships.c.sender_id,
                friendships.c.receiver_id,
                friendships.c.updated_at,
            ).where(friendships.c.status == "accepted")
        )
    ).all()

    active_temp_sessions = (
        await session.execute(
            select(func.count()).select_from(sessions).where(
                sessions.c.is_temp == True,
                sessions.c.status == "active",
            )
        )
    ).scalar_one()

    registered_devices = (
        await session.execute(select(func.count()).select_from(devices))
    ).scalar_one()

    active_device_ids: set[str] = set(broadcasting_ids)
    last_seen_map: dict[str, datetime] = {}
    last_message_map: dict[str, datetime] = {}
    bluetooth_pair_map: dict[tuple[str, str], dict[str, Any]] = {}

    for device_id, nearby_device_id, rssi, last_seen_at in recent_presence_rows:
        active_device_ids.add(device_id)
        active_device_ids.add(nearby_device_id)

        last_seen_map[device_id] = max(last_seen_map.get(device_id, last_seen_at), last_seen_at)
        last_seen_map[nearby_device_id] = max(
            last_seen_map.get(nearby_device_id, last_seen_at),
            last_seen_at,
        )

        source, target = sorted((device_id, nearby_device_id))
        edge = bluetooth_pair_map.setdefault(
            (source, target),
            {
                "source": source,
                "target": target,
                "kind": "bluetooth",
                "strength": 0,
                "samples": 0,
                "last_seen_at": last_seen_at,
                "rssi_sum": 0,
            },
        )
        edge["strength"] += 1
        edge["samples"] += 1
        edge["rssi_sum"] += rssi
        if last_seen_at > edge["last_seen_at"]:
            edge["last_seen_at"] = last_seen_at

    for sender_id, receiver_id, created_at in recent_message_rows:
        active_device_ids.add(sender_id)
        active_device_ids.add(receiver_id)
        last_message_map[sender_id] = max(last_message_map.get(sender_id, created_at), created_at)
        last_message_map[receiver_id] = max(last_message_map.get(receiver_id, created_at), created_at)

    friend_edge_map: dict[tuple[str, str], dict[str, Any]] = {}
    friend_neighbors: dict[str, set[str]] = defaultdict(set)
    for sender_id, receiver_id, updated_at in friendship_rows:
        source, target = sorted((sender_id, receiver_id))
        if source in active_device_ids or target in active_device_ids:
            active_device_ids.add(source)
            active_device_ids.add(target)
        friend_edge_map[(source, target)] = {
            "source": source,
            "target": target,
            "kind": "friendship",
            "strength": 1,
            "last_seen_at": updated_at,
        }
        friend_neighbors[source].add(target)
        friend_neighbors[target].add(source)

    candidate_query = (
        select(
            devices.c.device_id,
            devices.c.nickname,
            devices.c.avatar,
            devices.c.tags,
            devices.c.profile,
            devices.c.is_anonymous,
            devices.c.role_name,
            case(
                (devices.c.device_id.in_(broadcasting_ids), literal(True)),
                else_=literal(False),
            ).label("is_broadcasting"),
        )
        .where(devices.c.device_id.in_(active_device_ids))
    )
    device_rows = (await session.execute(candidate_query)).mappings().all()

    scored_rows = []
    for row in device_rows:
        device_id = row["device_id"]
        score = 0.0
        if row["is_broadcasting"]:
            score += 100
        if device_id in last_seen_map:
            age = max((now - last_seen_map[device_id]).total_seconds(), 0)
            score += max(0, 80 - age / 4)
        if device_id in last_message_map:
            age = max((now - last_message_map[device_id]).total_seconds(), 0)
            score += max(0, 40 - age / 30)
        score += len(friend_neighbors.get(device_id, set())) * 4
        scored_rows.append((score, row))

    scored_rows.sort(key=lambda item: (-item[0], item[1]["nickname"] or "", item[1]["device_id"]))
    visible_rows = [row for _, row in scored_rows[: settings.np_site_max_nodes]]
    visible_ids = {row["device_id"] for row in visible_rows}

    node_degree: dict[str, int] = defaultdict(int)
    edges = []
    for edge in bluetooth_pair_map.values():
        if edge["source"] in visible_ids and edge["target"] in visible_ids:
            node_degree[edge["source"]] += 1
            node_degree[edge["target"]] += 1
            edges.append(
                {
                    "source": edge["source"],
                    "target": edge["target"],
                    "kind": edge["kind"],
                    "strength": edge["strength"],
                    "avg_rssi": round(edge["rssi_sum"] / max(edge["samples"], 1), 2),
                    "last_seen_at": edge["last_seen_at"].isoformat() + "Z",
                }
            )

    for edge in friend_edge_map.values():
        if edge["source"] in visible_ids and edge["target"] in visible_ids:
            node_degree[edge["source"]] += 1
            node_degree[edge["target"]] += 1
            edges.append(
                {
                    "source": edge["source"],
                    "target": edge["target"],
                    "kind": edge["kind"],
                    "strength": edge["strength"],
                    "last_seen_at": edge["last_seen_at"].isoformat() + "Z",
                }
            )

    nodes = []
    for row in visible_rows:
        device_id = row["device_id"]
        nickname = row["nickname"] or "Unnamed"
        label = row["role_name"] if row["is_anonymous"] and row["role_name"] else nickname
        nodes.append(
            {
                "id": device_id,
                "label": label,
                "nickname": nickname,
                "role_name": row["role_name"],
                "avatar": row["avatar"],
                "tags": row["tags"] or [],
                "profile": row["profile"] or "",
                "is_anonymous": bool(row["is_anonymous"]),
                "is_broadcasting": bool(row["is_broadcasting"]),
                "degree": node_degree.get(device_id, 0),
                "friend_degree": len(friend_neighbors.get(device_id, set())),
                "last_seen_at": (
                    last_seen_map[device_id].isoformat() + "Z" if device_id in last_seen_map else None
                ),
                "last_message_at": (
                    last_message_map[device_id].isoformat() + "Z"
                    if device_id in last_message_map
                    else None
                ),
            }
        )

    bluetooth_active_ids = {
        device_id
        for edge in recent_presence_rows
        for device_id in (edge[0], edge[1])
    }

    stats = {
        "registered_devices": registered_devices,
        "broadcasting_devices": len(broadcasting_ids),
        "bluetooth_active_devices": len(bluetooth_active_ids),
        "visible_devices": len(nodes),
        "bluetooth_edges": sum(1 for edge in edges if edge["kind"] == "bluetooth"),
        "friendship_edges": sum(1 for edge in edges if edge["kind"] == "friendship"),
        "active_temp_sessions": active_temp_sessions,
    }

    hottest_devices = sorted(
        nodes,
        key=lambda node: (
            -int(node["is_broadcasting"]),
            -node["degree"],
            -node["friend_degree"],
            node["label"],
        ),
    )[:10]

    return {
        "generated_at": now.isoformat() + "Z",
        "refresh_seconds": settings.np_site_refresh_seconds,
        "windows": {
            "presence_seconds": settings.np_site_presence_seconds,
            "message_minutes": settings.np_site_message_minutes,
        },
        "stats": stats,
        "nodes": nodes,
        "edges": edges,
        "highlights": [
            {
                "id": node["id"],
                "label": node["label"],
                "degree": node["degree"],
                "friend_degree": node["friend_degree"],
                "is_broadcasting": node["is_broadcasting"],
            }
            for node in hottest_devices
        ],
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(settings.resolved_database_url, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: metadata.reflect(
                bind=sync_conn,
                only=[
                    "devices",
                    "temp_ids",
                    "presences",
                    "friendships",
                    "sessions",
                    "messages",
                ],
                resolve_fks=False,
            )
        )
    app.state.runtime = AppState(engine=engine, session_factory=session_factory)
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/live")
async def live_data() -> dict[str, Any]:
    runtime: AppState = app.state.runtime
    async with runtime.session_factory() as session:
        return await build_payload(session)
