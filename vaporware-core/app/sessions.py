from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.mqtt_bridge import SoundObserverBridge
from app.providers.tts import TTSProvider

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sessions"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LogEntry:
    timestamp: str
    event: str
    details: dict = field(default_factory=dict)


@dataclass
class Session:
    session_id: str
    started_at: str
    stopped_at: str | None = None
    services: dict = field(default_factory=dict)  # e.g. {"tts": {"name": "VoiceBox", "connected": True}}
    log: list[LogEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def append(self, event: str, **details) -> LogEntry:
        entry = LogEntry(timestamp=_now(), event=event, details=details)
        self.log.append(entry)
        return entry


class SessionManager:
    """The base unit of experience (06-sessions.md) — a general
    container, not tied to any single Ritual. This prototype attaches
    two direct services (TTS, SoundObserver), ahead of a full Ritual
    layer.
    """

    def __init__(self, tts_provider: TTSProvider, sound_observer_bridge: SoundObserverBridge):
        self.tts_provider = tts_provider
        self.sound_observer_bridge = sound_observer_bridge
        self.current: Session | None = None

    def start(self, observers: list[str] | None = None) -> Session:
        if self.current is not None:
            raise ValueError("a session is already active — stop it first")
        observers = observers or []

        session = Session(session_id=str(uuid.uuid4()), started_at=_now())
        session.append("session_started", observers=observers)

        # TTS is an Actuator (04-actuators.md) — invoked on demand, not
        # gated by the session's observer list. Always health-checked.
        tts_status = self.tts_provider.check_connection()
        session.services["tts"] = {
            "name": "VoiceBox",
            "connected": tts_status.connected,
            "detail": tts_status.detail,
            "profiles": [p.name for p in tts_status.profiles],
        }
        session.append(
            "tts_connected" if tts_status.connected else "tts_connection_failed",
            detail=tts_status.detail,
            profiles=[p.name for p in tts_status.profiles],
        )

        # Observers (03-components.md) run as independent satellite
        # projects (see ../../VaporwareSoundObserver) and publish events over
        # MQTT — Vaporware core just subscribes. A session including
        # an observer means "log its events while I'm active," not
        # "start its process": that process runs on its own regardless.
        if "sound_observer" in observers:
            connected = self.sound_observer_bridge.connected
            session.services["sound_observer"] = {
                "name": "SoundObserver (MQTT)",
                "included": True,
                "connected": connected,
                "detail": "Subscribed to soundobserver/speech/transcribed"
                if connected
                else "MQTT broker unreachable",
            }
            session.append(
                "sound_observer_connected" if connected else "sound_observer_connection_failed",
                detail=session.services["sound_observer"]["detail"],
            )

        self.current = session
        self._persist(session)
        return session

    def stop(self) -> Session:
        if self.current is None:
            raise ValueError("no active session")

        session = self.current
        session.stopped_at = _now()
        session.append("session_stopped")
        self._persist(session)
        self.current = None
        return session

    def speak(self, text: str, profile: str | None = None) -> LogEntry:
        if self.current is None:
            raise ValueError("no active session")
        if not self.current.services.get("tts", {}).get("connected"):
            raise ValueError("TTS is not connected in this session")

        result = self.tts_provider.speak(text, profile=profile)
        entry = self.current.append(
            "tts_speak",
            text=text,
            profile=profile,
            ok=result.ok,
            detail=result.detail,
        )
        self._persist(self.current)
        return entry

    def record_observer_event(self, payload: dict) -> LogEntry | None:
        """Called by the MQTT bridge when SoundObserver publishes a
        transcript. Only logged if the active session actually
        included sound_observer — otherwise SoundObserver may be
        running for someone/something else's session entirely.
        """
        if self.current is None:
            return None
        if not self.current.services.get("sound_observer", {}).get("included"):
            return None

        entry = self.current.append(
            "sound_observer_transcribed",
            text=payload.get("text"),
            duration=payload.get("duration"),
            mode=payload.get("mode"),
        )
        self._persist(self.current)
        return entry

    def list_sessions(self) -> list[dict]:
        sessions = []
        for path in DATA_DIR.glob("*.json"):
            with path.open() as f:
                sessions.append(json.load(f))
        sessions.sort(key=lambda s: s["started_at"], reverse=True)
        return sessions

    def get_session(self, session_id: str) -> dict | None:
        path = DATA_DIR / f"{session_id}.json"
        if not path.exists():
            return None
        with path.open() as f:
            return json.load(f)

    def _persist(self, session: Session) -> None:
        path = DATA_DIR / f"{session.session_id}.json"
        with path.open("w") as f:
            json.dump(session.to_dict(), f, indent=2, default=str)
