import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .aliases import DeviceAliasStore
from .config import settings
from .providers import DemoProvider, TDW9970Provider, TrafficService

BASE_DIR = Path(__file__).resolve().parent.parent
provider = TDW9970Provider(settings) if settings.mode == "router" else DemoProvider()
service = TrafficService(provider, settings.poll_interval)
aliases = DeviceAliasStore(BASE_DIR / "data" / "device_names.json")


class DeviceNameUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=40)


def current_payload() -> dict:
    payload = service.payload()
    for device in payload["devices"]:
        device["name"] = aliases.get(device["mac"]) or device["name"]
    return payload


@asynccontextmanager
async def lifespan(_: FastAPI):
    await service.start()
    yield
    await service.stop()


app = FastAPI(title="Ağ Gözcüsü", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/status")
async def status():
    return {**current_payload(), "mode": settings.mode, "router": settings.router_url}


@app.put("/api/devices/{mac}/name")
async def update_device_name(mac: str, update: DeviceNameUpdate):
    try:
        name = aliases.set(mac, update.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"mac": aliases.normalize_mac(mac), "name": name}


@app.websocket("/ws")
async def websocket_feed(socket: WebSocket):
    await socket.accept()
    try:
        while True:
            await socket.send_json({**current_payload(), "mode": settings.mode})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
