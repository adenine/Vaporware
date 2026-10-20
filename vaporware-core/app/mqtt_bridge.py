from __future__ import annotations

import json
from typing import Callable

import paho.mqtt.client as mqtt


class SoundObserverBridge:
    """Subscribes to the standalone SoundObserver project's MQTT
    events (see ../../VaporwareSoundObserver) and forwards them to whatever
    callback the active session wants. Vaporware core does not run
    any mic capture or call VoiceBox directly for audio — that's
    SoundObserver's job now; this is just the subscriber side of the
    Observer -> Base pipeline described in 03-components.md.
    """

    def __init__(
        self,
        on_transcript: Callable[[dict], None],
        host: str = "localhost",
        port: int = 1883,
        topic_base: str = "soundobserver",
    ):
        self._on_transcript = on_transcript
        self._topic_base = topic_base
        self._connected = False
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._host = host
        self._port = port

    def start(self):
        try:
            self._client.connect_async(self._host, self._port)
            self._client.loop_start()
        except Exception:  # noqa: BLE001
            self._connected = False

    def stop(self):
        self._client.loop_stop()
        self._client.disconnect()

    @property
    def connected(self) -> bool:
        return self._connected

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        if not reason_code.is_failure:
            self._connected = True
            client.subscribe(f"{self._topic_base}/speech/transcribed")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self._connected = False

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        self._on_transcript(payload)
