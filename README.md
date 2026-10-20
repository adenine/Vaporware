# Vaporware

A local-first AI operating layer that senses and acts across the full
surface of your life — not one app, but a substrate that wires together
off-the-shelf tools and custom glue, coordinated by local AI with
persistent memory of *you*, so it can both **capture** (sense, log,
remember) and **act** (automate, suggest, execute) on your behalf.

Everything runs on hardware you own. This is an early, draft-stage
project: the design docs are working sketches, and the code is a
prototype.

## Design docs

| Doc | What it covers |
|---|---|
| [`00-vision.md`](00-vision.md) | The one-liner, the problem, design tenets, non-goals |
| [`01-taxonomy.md`](01-taxonomy.md) | The six life domains, each with a sensing and an acting side |
| [`02-architecture.md`](02-architecture.md) | Core architecture and layers |
| [`03-components.md`](03-components.md) | Observers (perception) and Controls (input) |
| [`04-actuators.md`](04-actuators.md) | Actuators (real-world output) |
| [`05-rituals.md`](05-rituals.md) | Rituals: named, prompt-defined units of orchestration |
| [`06-sessions.md`](06-sessions.md) | Sessions: the base unit of experience |
| [`07-providers.md`](07-providers.md) | Providers: the loose-coupling pattern for swappable capabilities |
| [`08-test-experiences.md`](08-test-experiences.md) | First end-to-end tests: Magic Word and Presence Light |

## Observers

Observers are the sensing side of Vaporware: each one turns a raw
signal (camera, microphone, sensors, online services) into structured
events, published over MQTT and/or Spacebrew 2.0.

Each Observer is an independent piece of software. It can be used on its
own, together with the other Observers and tools, and with or without
the Vaporware service.

| Observer | What it does |
|---|---|
| [VaporwareVisualObserver](https://github.com/adenine/VaporwareVisualObserver) | Detects and tracks people and objects in a camera feed and publishes enter/exit/location events, with switchable privacy modes. The successor to OpenTSPS. |
| [VaporwareSoundObserver](https://github.com/adenine/VaporwareSoundObserver) | Listens on a microphone, transcribes speech and classifies sounds through switchable engines, and can speak through TTS outputs. |
| [VaporwareEnvironmentObserver](https://github.com/adenine/VaporwareEnvironmentObserver) | Polls location, place, weather, and air quality sensors and services on a timer, and publishes the conditions of the space around you. |
| [VaporwareDigitalServiceObserver](https://github.com/adenine/VaporwareDigitalServiceObserver) | Observes your presence and activity in digital services. Just getting started. |

## Repo layout

```
vaporware-core/        FastAPI admin prototype (sessions, TTS, MQTT bridge)
examples/
  WebExamples/         Browser pages driven by Spacebrew (ContextStory, VisualStory)
  ProcessingExamples/  Processing sketches driven by Spacebrew (MagicWord)
```

## vaporware-core

A prototype web admin interface for starting and stopping Sessions. Each
session logs its events (TTS output, SoundObserver transcripts) to
`vaporware-core/data/sessions/` as JSON, and past sessions can be browsed
from the admin page.

```sh
cd vaporware-core
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000
```

Then open http://127.0.0.1:8000.

Optional local services it connects to:

- **VoiceBox** (TTS) at `http://127.0.0.1:17493`
- **MQTT broker** (e.g. Mosquitto) at `localhost:1883`, which carries
  SoundObserver transcripts on `soundobserver/speech/transcribed`

The admin page still runs without them; the session shows those services
as not connected.

## Examples

The examples are Spacebrew 2.0 clients: they need Spacebrew running
locally (WebSocket gateway at `ws://localhost:8088/ws/client`).

**Web examples.** Each one is a single `index.html` with nothing to build.
Open it in a browser, then publish to its topics. The header comment in
each file lists sample commands, for example:

```sh
curl -X POST http://localhost:8088/api/publish -H "Content-Type: application/json" \
  -d '{"topic": "VisualStory/observedEntered", "message": "dog"}'
```

Add `?host=...&port=...` to the page URL if Spacebrew isn't on
`localhost:8088`.

**Processing examples.** Open the `.pde` sketch in Processing. They need
the MQTT library by Joel Gaehwiler (Sketch → Import Library → Add
Library…).

## License

[MIT](LICENSE)
