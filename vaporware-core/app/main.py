from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from app.mqtt_bridge import SoundObserverBridge
from app.providers.tts import VoiceBoxTTSProvider
from app.sessions import SessionManager

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Vaporware admin (prototype)")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
jinja_env = Environment(loader=FileSystemLoader(BASE_DIR / "templates"), autoescape=True)

manager = SessionManager(
    tts_provider=VoiceBoxTTSProvider(),
    sound_observer_bridge=SoundObserverBridge(on_transcript=lambda payload: manager.record_observer_event(payload)),
)


@app.on_event("startup")
def _start_mqtt_bridge():
    manager.sound_observer_bridge.start()


@app.on_event("shutdown")
def _stop_mqtt_bridge():
    manager.sound_observer_bridge.stop()


class SpeakRequest(BaseModel):
    text: str
    profile: str | None = None


class StartSessionRequest(BaseModel):
    observers: list[str] = []


@app.get("/", response_class=HTMLResponse)
def admin_page():
    template = jinja_env.get_template("admin.html")
    html = template.render(
        current=manager.current.to_dict() if manager.current else None,
        history=manager.list_sessions(),
    )
    return HTMLResponse(content=html)


@app.post("/api/sessions/start")
def start_session(req: StartSessionRequest = StartSessionRequest()):
    try:
        session = manager.start(observers=req.observers)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return session.to_dict()


@app.post("/api/sessions/stop")
def stop_session():
    try:
        session = manager.stop()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return session.to_dict()


@app.get("/api/sessions/current")
def current_session():
    return manager.current.to_dict() if manager.current else None


@app.post("/api/sessions/speak")
def speak(req: SpeakRequest):
    try:
        entry = manager.speak(req.text, profile=req.profile)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"entry": entry, "session": manager.current.to_dict()}


@app.get("/api/sessions")
def list_sessions():
    return manager.list_sessions()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    session = manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session
