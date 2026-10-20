# Vaporware — Component Catalog: Observers & Controls (draft v0)

## The "Observer" pattern

An **Observer** is a modality-specific perception module: it consumes
raw signal from sensors and emits structured events into the Memory
layer (`02-architecture.md`). It sits between raw capture and memory —
not just moving bytes (that's a plain adapter), but interpreting them
(CV inference, audio classification, sensor readings → labeled
events).

```
raw signal (camera/mic/sensor) → [Observer: perception/inference] → structured event → Memory
```

Common shape every Observer should share (draft):

- **Input:** one or more raw sensor streams.
- **Processing:** off-the-shelf models/libraries where good ones
  exist; custom only where needed.
- **Output:** structured events (typed, timestamped, tagged with
  domain and confidence) written to Memory — not raw signal, unless
  raw retention is an explicit, separate decision per Observer.
- **Privacy tier:** how sensitive the output (and any retained raw
  signal) is. See below — this varies enormously across Observers.
- **Primary base:** which base(s) run the actual inference. Raw
  capture can happen anywhere (a camera, a mic, a sensor on any base),
  but heavy inference likely centralizes on Homebase for compute and
  privacy reasons (data doesn't need to leave the premises).
  Concretely, an Observer often runs on its own **dedicated satellite
  node** — a separate machine whose only job is that Observer's
  inference — and streams structured events to whichever base is
  running Reasoning/Memory (typically Homebase). See the worked
  example in `05-rituals.md` for a VisualObserver + SoundObserver each
  on their own machine, feeding one Vaporware core.

## Privacy tiers (draft — feeds into Governance)

| Tier | Meaning | Example |
|---|---|---|
| T1 — Ambient | Non-identifying, low sensitivity | Particulate counts, ambient noise dB level |
| T2 — Identifying | Reveals presence/identity/activity but not content | "A person is in the kitchen," "a dog barked," species ID of a bird call |
| T3 — Content | Captures the substance of what was said/done | Conversation transcripts, recognized speech content, facial identification tied to a person |

Raw video/audio retention (vs. discard-after-inference) should be a
per-Observer, explicit, opt-in decision — default to **discard raw,
keep structured event only**, especially for T3 outputs.

**T1/T2/T3 is a content-sensitivity axis, not the same thing as a
per-Observer Privacy Mode (1/2/3).** SoundObserver's real implementation
(see below) forced this apart: its Mode 1 ("no speaker identity
attached") still produces T3 content (a full conversation transcript) —
identity attribution and content sensitivity vary independently, they
don't move together. Treat "Mode N" as *whose* signal it is; T1/T2/T3
as *how sensitive* the content is regardless of whose it's attributed
to.

## VisualObserver

*(Renamed from LifeObserver — same project, now at
[`../VaporwareVisualObserver`](../VaporwareVisualObserver) on disk,
calling itself "VisualObserver" internally. Successor to
[OpenTSPS](http://opentsps.com/), by its own README.)*

**Real, running project** — unlike when this catalog was first drafted
(when LifeObserver was still a bullet list of candidates to evaluate),
it now exists with the same shape as SoundObserver below: Python, PyQt6
desktop app, a 3-tier Privacy Mode enum (identity-attribution axis, see
the note above), MQTT publisher-only, QSettings-based config.

- **Modality:** computer vision.
- **Purpose:** understand how people move through a physical space —
  detection, tracking, and (Mode 2/3) re-identification/attribution.
  Narrower today than this doc's original "people, pets, wildlife,
  activity recognition" aspiration — the real project is scoped to
  person detection/tracking, not yet pet/wildlife/activity recognition.
- **Privacy modes (implemented):**
  - Mode 1 — Anonymized Realtime: `PersonEntered`/`PersonExited`
    (centroid, bounding box) and `PersonLocation`, no identity.
    **Working** — YOLOv8n or OpenCV MOG2/KNN detection, ByteTrack
    tracking.
  - Mode 2 — Anonymized Recognition: adds `NewPerson`/`RecognizedPerson`,
    anonymous numeric ID persisted across sessions via embeddings (no
    images stored). **Working** — StrongSORT + OSNet-x0.25 re-ID,
    SQLite embedding store.
  - Mode 3 — Identified Recognition: adds `PersonalMetaData` (emotion,
    age, gender, race, free-text LLM description) tied to a named
    identity, PII encrypted at rest (SQLCipher). **Stub** — DeepFace
    identity/attributes and an Ollama+LLaVA description path are both
    unimplemented placeholders.
  - Notably *more* built out than SoundObserver's Mode 2/3 (which are
    both still stubs) — VisualObserver's re-identification (Mode 2) is
    real, working recognition, not just a plan.
- **MQTT events** (topic base `visualobserver`, configurable):
  `visualobserver/person/entered`, `/exited`, `/location` — payload
  includes `id`, `centroid`, `bbox`, and `mode`.
- **Example events (aspirational, not yet built):** activity recognition
  (cooking, exercising, sleeping), pet behavior, wildlife sightings —
  still the eventual scope per this doc's original framing, just not
  where the real project's effort has gone yet.
- **Feeds domains:** Environment (occupancy), People (who's present,
  behavior), Self (activity recognition), Stories (memorable moments).
- **Privacy tier:** T2 by default (presence/activity, Mode 1); T3 the
  moment Mode 3's named-identity + attribute data exists in a retained
  record. The most sensitive Observer by surface area — cameras see the
  most — and now the Observer with the most privacy-relevant
  functionality actually implemented (Mode 2 re-ID working, unlike
  SoundObserver's speaker-ID stubs).
- **Primary base:** Homebase (compute-heavy inference); camera hardware
  itself could be anywhere.
- **Deployment tiers (per the project's own table):** laptop/Jetson
  Orin Nano for Modes 1–3, Raspberry Pi 4/5 for Modes 1–2, ESP32/Arduino
  as MQTT-subscriber-only — same three-tier shape as SoundObserver's,
  worth treating as the emerging standard shape for `02-architecture.md`'s
  base tiers to reconcile against.

## SoundObserver

*(Renamed from AudioObserver — same project, now at
[`../VaporwareSoundObserver`](../VaporwareSoundObserver) on disk,
calling itself "SoundObserver" internally. `vaporware-core`'s bridge
code has caught up to the AudioObserver→SoundObserver naming, but not
yet to the folder move to `VaporwareSoundObserver` — see the Naming
note below.)*

**Real, running project** — extracted from an embedded prototype in
`vaporware-core` into its own standalone project, matching
[VisualObserver](../VaporwareVisualObserver)'s established shape:
Python, PyQt6 desktop app, a 3-tier Privacy Mode enum, QSettings-based
config. It has grown well past VisualObserver's shape in one respect
though — see "No longer input-only" below. Vaporware core no longer
runs any mic capture or calls VoiceBox directly for audio — it just
subscribes to SoundObserver's MQTT topic (`app/mqtt_bridge.py`) and
logs whatever it publishes into the active Session. This is the
concrete implementation of the "dedicated satellite node" pattern
described above.

- **Modality:** audio.
- **Purpose:** understand conversation, ambient/environmental sound
  events, and (new) speak back — see outputs below.
- **Inputs are now multi-engine and independently switchable** (not
  one VoiceBox integration): **VoiceBox STT**, **Apple Native STT**
  (on-device `Speech.framework`, no external service), and **YAMNet**
  (local ambient-sound classification, `.tflite` via `ai-edge-litert`,
  ~1s cadence independent of the STT chunk timer). Running more than
  one STT engine at once produces one tagged event per engine per
  utterance (`source: apple` / `voicebox`) — a Ritual subscribing to
  transcripts needs to expect possible duplicates if both are on, not
  assume one event per utterance.
- **Privacy modes (implemented) — the tiers are about *identity
  attribution*, not whether content is captured.** This inverts what
  was assumed here originally (see Superseded note):
  - Mode 1 — Anonymized Realtime: `SpeechTranscribed` (full transcript
    + duration, **no speaker identity attached**) and `SoundDetected`
    (YAMNet label + confidence). **Working**, and the *default* mode —
    both input recognizers are gated by this same Mode 1 check, so
    events publish as soon as a session starts, no mode switch needed.
  - Mode 2 — Anonymized Recognition: adds `SpeakerEntered`/`Exited`,
    anonymous voice-print-matched ID, no name. **Stub.**
  - Mode 3 — Identified Recognition: same as Mode 2 with a real name
    attached instead of an anonymous ID. **Stub.**
  - Net effect: full-transcript capture (T3 content per the tiers
    above) now happens in the *least* identity-revealing mode. Modes 2
    and 3 layer on speaker recognition; they don't gate transcription
    itself. Still the Observer most in need of an explicit on/off or
    wake-word gate given Mode 1's T3 content, just not for the reason
    originally assumed here (it's not behind a "highest mode," it's the
    default).
- **MQTT events** (topic base `soundobserver`, configurable):
  `soundobserver/speech/transcribed` (working), `soundobserver/sound/
  detected` (working, via YAMNet), `soundobserver/speaker/entered`
  `/exited` (stubs) — see the project's README for payload shapes.
- **No longer input-only — publisher-only no longer holds.** SoundObserver
  now also has **output** engines (Apple Native TTS, VoiceBox TTS, plus
  a not-yet-built Song Generator stub), driven by a `tts` message on its
  own Spacebrew `SoundObserver/tts` topic, and it publishes to Spacebrew
  2.0 (`word`, `segments`, `sound_detected`) in addition to MQTT. That
  makes it simultaneously an Observer (input, MQTT) and something that
  behaves like an Actuator (audio output, Spacebrew-triggered) inside
  one process — worth resolving explicitly against `04-actuators.md`'s
  `AudioActuator` and `07-providers.md`'s `TTSProvider` rather than
  letting two parallel TTS paths (Vaporware core's and SoundObserver's
  own) grow independently. See open question below.
- **Feeds domains:** People (conversation/communication context —
  highest sensitivity), Environment (ambient/traffic sound,
  quality-of-life), Self (possible stress/noise correlation).
- **Privacy tier:** spans all three — ambient sound-event confidence is
  T1/T2 depending on label specificity, a transcribed conversation is
  T3, regardless of which identity Mode is active (see the T1/T2/T3
  vs. Mode-N note above).
- **Primary base:** runs as its own process, anywhere with a mic —
  Homebase for the always-on installation case, but nothing prevents
  running it on Travelbase too. The project's own deployment-tier table
  (laptop/Jetson for Modes 1–3, Raspberry Pi for Modes 1–2, ESP32/
  Arduino as MQTT-subscriber-only actuator) is a useful reference if/
  when Vaporware's own base tiers (`02-architecture.md`) need to line up
  against it.

### Real-world gotcha (worth remembering)

Running SoundObserver's Python venv *inside* the iCloud-synced project
folder broke PyQt6 at startup — `qt.qpa.plugin: Could not find the Qt
platform plugin "cocoa"` — even though the plugin file itself loaded
fine via a plain `dlopen`. Fixed by creating the venv outside iCloud
Drive (`~/.venvs/soundobserver`) while keeping the source in the
iCloud project folder. Likely affects any PyQt/PySide project stored
under `~/Library/Mobile Documents/`, including VisualObserver — not
confirmed there yet, since VisualObserver's own README doesn't document
hitting this (may not have created an in-place `.venv` at all).

### Naming note

Resolved: `vaporware-core`'s bridge code (`app/mqtt_bridge.py`,
`app/sessions.py`, `app/main.py`, and the admin UI) now uses
`SoundObserverBridge` / `topic_base="soundobserver"` / a
`sound_observer` service key throughout, matching the standalone
project's real topics. The one thing that's just cosmetic (path
comments pointing at `../../VaporwareSoundObserver`) was updated too —
nothing left to reconcile on the SoundObserver side.

## EnvironmentObserver

*(Renamed from AirObserver — a folder now exists at
[`../VaporwareEnvironmentObserver`](../VaporwareEnvironmentObserver),
currently empty, signaling the intent to build this next but nothing
implemented yet. Unlike SoundObserver/VisualObserver above, there's no
real project to reconcile this section against — everything below is
still this doc's own plan, not a description of running code. The name
change to "Environment" (from "Air") tracks what this doc already said
below: scope was always meant to expand past particulates to other
gases/chemicals, so "Environment" fits the eventual scope better than
"Air" did.)*

- **Modality:** air quality sensing.
- **Purpose:** currently particulates (PM2.5/PM10); expanding to other
  gases/chemicals (CO2, VOCs, CO, radon, etc.) over time.
- **Example events:** particulate concentration readings, air-quality-
  index-style summaries, gas/chemical concentration alerts (future).
- **Off-the-shelf building blocks (candidates):** existing air-quality
  sensor modules and their reference firmware/drivers — mostly a
  hardware-integration problem plus threshold/alerting logic.
- **Feeds domains:** Environment (air quality itself), Self (health
  correlation — e.g. symptom flare-ups vs. particulate spikes).
- **Privacy tier:** T1 almost always — low sensitivity, though location
  + time-series of "who was home when air quality was bad" could
  weakly correlate to presence. Least sensitive Observer by far.
- **Primary base:** Homebase for aggregation; sensor hardware is
  physically fixed (home) or portable (a travel/wearable air sensor is
  plausible later).

## Observer comparison

| | **VisualObserver** | **SoundObserver** | **EnvironmentObserver** |
|---|---|---|---|
| Modality | Vision | Audio | Chemical/particulate sensors |
| Peak privacy tier | T3 (identity + attributes, Mode 3) | T3 (conversation content, in its default Mode) | T1 (ambient readings) |
| Compute cost | High (CV inference) | High (transcription), low (YAMNet event classification) | Low (sensor polling) |
| Needs explicit consent gating? | Yes — especially for guests | Yes — especially for transcription | No |
| Raw signal retention default | Discard after inference | Discard after inference | N/A — already structured |
| Real, running project? | Yes — `../VaporwareVisualObserver` | Yes — `../VaporwareSoundObserver` | No — plan only |

---

## Direct Input / Controls — Spacebrew 2.0

Controls are a different kind of input than Observers: a dial, knob,
or slider's position **is already structured data** — there's no
perception/inference step between raw signal and meaning. Where
Observers *interpret* ambiguous signal (is that a bark or a growl?),
Controls carry **explicit, user-intentional** signal (the user turned
this knob to 70%). This is a plumbing problem, not a perception
problem.

- **Technology (decided):** [Spacebrew 2.0](https://github.com/adenine/Spacebrew2.0)
  — "a dynamic re-routable software toolkit for choreographing
  interactive spaces utilizing MQTT." A Python router server sits
  between devices and an MQTT broker; a web dashboard (React + Rete.js)
  provides a visual patch-bay for wiring publishers to subscribers and
  rerouting live, without touching device code. A WebSocket gateway
  serves browser-based clients; MQTT Last Will handles clean
  disconnect detection.
- **What it connects:** any MQTT-capable client — Arduino/
  microcontroller-driven dials/knobs/sliders, Processing sketches, web/
  JS clients, Python scripts. Not limited to physical controls, but
  that's the driving use case here.
- **Why it matters architecturally:** it's the same *kind* of thing as
  the Relay base — infrastructure/plumbing, not a brain. Spacebrew
  doesn't decide anything; it routes named topics between publishers
  and subscribers so the Reasoning layer (or a human, via the patch
  bay) decides what's wired to what.
- **How it fits the five-layer model:** Controls are a second
  sub-layer of Sensing/Capture, alongside Observers — but because the
  signal is already structured, a control's MQTT message can feed
  Memory (or even Reasoning) directly, skipping the
  perception/inference step Observers require.
- **Feeds domains:** control-agnostic — the domain depends entirely on
  what a given dial is patched to (a "mood" slider → Self; a manual
  scene-override knob → Environment; a "do not disturb" toggle →
  People). The patch bay is where that binding happens, potentially
  even by the user at runtime.
- **Primary base:** Homebase, most likely — MQTT broker + router as
  always-on home infrastructure. Portable control surfaces on
  Travelbase are plausible later.
- **Privacy tier:** T2 at most, generally — a control's value reveals
  intent/state but rarely raw content. Lower sensitivity than
  VisualObserver/SoundObserver by default.

### Open questions (Controls-specific)

- **Bidirectional / actuation** — can Spacebrew also drive motorized
  dials/sliders as feedback (system moves a physical control to show
  state), or is this v0 read-only input? That would make Controls
  double as an Actuation-layer adapter, not just Sensing.
- **Network exposure** — MQTT traffic should stay on the Homebase LAN
  by default; if Travelbase/Wearable need to publish to it remotely,
  that's exactly the kind of traffic the Relay base should tunnel,
  not something to expose directly.
- **First real controls** — what's the first physical panel/device you
  want wired up? Concrete enough to prototype the patch-bay → Memory
  binding end to end.

---

## Open questions (to discuss)

- **Naming/scope convention** — "Observer" seems to be your term for
  any perception module in the Sensing layer. Should we formalize this
  now as a plugin interface (a spec every future Observer implements),
  or let the pattern emerge from these three first?
- **What other Observers do you already have in mind?** e.g. a
  presence/location Observer (distinct from VisualObserver's CV-based
  presence?), a biometric Observer (wearable health data), a
  digital-activity Observer (screen time, app usage)? Worth listing
  now even if undesigned, so the taxonomy in `01-taxonomy.md` and this
  catalog stay in sync.
- **Consent model for guests** — VisualObserver and SoundObserver both
  capture people who aren't you and haven't opted in (visitors, kids,
  neighbors' dogs). Needs a real answer before any of this runs live,
  not just a "T3 = sensitive" label.
- **Raw retention exceptions** — are there cases you *want* raw
  retention (e.g. a security-camera clip on an anomaly) despite the
  discard-by-default rule?
- **Is an Observer that also has outputs still just an Observer?**
  SoundObserver's TTS outputs (driven by its own Spacebrew `tts` topic)
  make it look like an Observer/Actuator hybrid, not a pure Sensing
  component. Does this pattern get its own name, does Vaporware core's
  `AudioActuator`/`TTSProvider` just delegate to SoundObserver's outputs
  over Spacebrew instead of maintaining a second TTS path, or is
  SoundObserver's TTS a standalone/local speak-back feature that's out
  of scope for Vaporware core entirely? See `04-actuators.md` and
  `07-providers.md`.

## Status

Draft v0, written 2026-07-03, updated 2026-07-11 for the AudioObserver
→ SoundObserver rename and its expanded scope (multi-engine STT/sound
classification inputs, TTS outputs, Spacebrew 2.0, inverted Mode 1/3
semantics), and updated again same day for the LifeObserver →
VisualObserver rename (now a real project too, with working Mode 1/2
recognition) and AirObserver → EnvironmentObserver rename (still plan-
only — an empty project folder exists but nothing's built). All three
satellite projects now live under `Vaporware<Modality>Observer` folder
names (`VaporwareVisualObserver`, `VaporwareSoundObserver`,
`VaporwareEnvironmentObserver`) while keeping their short internal
names (VisualObserver, SoundObserver, EnvironmentObserver) — this doc
uses the short names in prose and the full folder name only in path
links. Cross-references: `01-taxonomy.md` (domains these feed),
`02-architecture.md` (Sensing/Capture layer and which base runs
inference).
