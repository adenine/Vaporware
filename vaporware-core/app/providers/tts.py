from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx


@dataclass
class Profile:
    id: str
    name: str


@dataclass
class ConnectionStatus:
    connected: bool
    detail: str
    profiles: list[Profile]


@dataclass
class SpeakResult:
    ok: bool
    detail: str


class TTSProvider(ABC):
    """Stable interface AudioActuator/admin backend code depends on.

    Swapping the implementation (e.g. away from VoiceBox) should never
    require changing callers of this interface. See 07-providers.md.
    """

    @abstractmethod
    def check_connection(self) -> ConnectionStatus: ...

    @abstractmethod
    def speak(self, text: str, profile: str | None = None) -> SpeakResult: ...


class VoiceBoxTTSProvider(TTSProvider):
    def __init__(self, base_url: str = "http://127.0.0.1:17493", timeout: float = 10.0):
        self.base_url = base_url
        self.timeout = timeout

    def check_connection(self) -> ConnectionStatus:
        try:
            resp = httpx.get(f"{self.base_url}/profiles", timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.json()
            profiles = [Profile(id=p["id"], name=p["name"]) for p in raw]
            return ConnectionStatus(
                connected=True,
                detail=f"VoiceBox reachable at {self.base_url}",
                profiles=profiles,
            )
        except Exception as exc:  # noqa: BLE001 - surface any failure as disconnected
            return ConnectionStatus(
                connected=False,
                detail=f"VoiceBox unreachable at {self.base_url}: {exc}",
                profiles=[],
            )

    def speak(self, text: str, profile: str | None = None) -> SpeakResult:
        payload: dict = {"text": text}
        if profile:
            payload["profile"] = profile
        try:
            resp = httpx.post(f"{self.base_url}/speak", json=payload, timeout=self.timeout)
            if resp.status_code >= 400:
                return SpeakResult(ok=False, detail=f"{resp.status_code}: {resp.text}")
            return SpeakResult(ok=True, detail="spoken")
        except Exception as exc:  # noqa: BLE001
            return SpeakResult(ok=False, detail=str(exc))
