# Vaporware — Providers: the loose-coupling pattern (draft v0)

## The pattern

Anywhere Vaporware depends on a capability that has multiple, fast-
changing candidate implementations — text-to-speech today, likely
speech-to-text, image generation, and video generation later — it
should depend on a small **stable internal interface**, not on any
one library or model directly. Concrete implementations behind that
interface are **Providers**; swapping one out for a newer/better one
should mean a config change in the admin UI, not a code change in the
Actuator or Reasoning layer that calls it.

```
Actuator/Reasoning code → [stable interface] → active Provider (swappable)
                                              → Piper, Kokoro, Chatterbox, XTTS v2, ...
```

This is tenet 2 from `00-vision.md` ("loosely coupled, not a
monolith") made concrete. TTS is the first worked example because it
illustrates exactly why this matters: the field is moving fast enough
that a hardcoded choice made today is likely wrong in six months (see
the Piper license change below, which happened mid-flight).

## Worked example: `TTSProvider`

A minimal interface, conceptually:

- **Input:** text, a voice/style selector, optional constraints
  (latency budget, target language).
- **Output:** an audio stream, routed to `AudioActuator`
  (`04-actuators.md`).
- **Capability metadata**, so Reasoning/admin can pick the right
  Provider for the situation rather than always using one fixed
  choice: supports voice cloning? language coverage? real-time
  factor (faster/slower than real-time)? license (commercial-safe or
  not)?

The registry of available Providers, and which one is active (or
active per use case), lives in the admin interface
(`02-architecture.md`) — this is where you'd swap engines, not in
code.

### Current local TTS landscape (as of mid-2026)

| Provider | License | Voice cloning | Size/compute | Notes |
|---|---|---|---|---|
| **Piper** | MIT (original, archived Oct 2025) → active fork is **GPL-3.0** | No | Tiny — runs on a Raspberry Pi 4 | Best choice for the lowest-compute satellite nodes; the license change mid-flight is the exact scenario this pattern protects against. |
| **Kokoro** | Apache-2.0 | No (54 fixed voices, 8 languages) | 82M params, faster than real-time on CPU | Best efficiency/quality balance for a fully permissive license; good Homebase default when cloning isn't needed. |
| **Chatterbox** (Resemble AI) | MIT | Yes (~5s reference) | Moderate | Reportedly preferred over ElevenLabs in blind tests; adds an emotion-exaggeration control. Best pick if you want a cloned voice and to stay commercial-safe. |
| **XTTS v2** (Coqui) | CPML — **non-commercial only** | Yes (~6s reference), 17 languages | Moderate–heavy | Best-in-class cloning quality, but the license blocks anything beyond personal/non-commercial use — flag this if Vaporware ever stops being just-for-you. |
| **F5-TTS** | CC-BY-NC 4.0 — non-commercial | Yes | Moderate | Same license caveat as XTTS v2. |
| **Bark**, **Dia**, **Parler-TTS**, **Fish Speech** | Apache-2.0/MIT (varies) | Varies | Varies | Worth a look for creative/expressive audio beyond narration; not evaluated in depth here. |

### VoiceBox — an off-the-shelf implementation of this whole pattern

[VoiceBox](https://voicebox.sh) (jamiepine/voicebox on GitHub) is a
free, open-source, local-first "voice studio" app that **already does
what this section proposes**: one interface in front of 7 swappable
TTS engines (Qwen3-TTS, Qwen CustomVoice, Chatterbox Multilingual,
Chatterbox Turbo, LuxTTS, Kokoro 82M, HumeAI TADA), plus voice cloning
from a few seconds of audio, everything running locally with no cloud
call and no account. Two details make it especially relevant here:

- **Dictation, not just synthesis** — a global-hotkey speech-to-text
  feature overlaps with the `ASRProvider` need under SoundObserver's
  transcription path (`03-components.md`). One tool, potentially both
  sides of the Audio Actuator/SoundObserver pair — note this pairing is
  no longer symmetric by name (`AudioActuator` vs. `SoundObserver`)
  since only the input side got renamed; flagging in case that's worth
  fixing for consistency rather than leaving as a historical artifact.
- **Two integration surfaces, confirmed live on `127.0.0.1:17493`:**
  a plain REST API (`POST /speak`, `POST /generate`, `POST
  /transcribe`, `GET /profiles`) and an MCP server (`/mcp`, tools
  `voicebox.speak`/`.transcribe`/`.list_captures`/`.list_profiles`,
  requiring an `X-Voicebox-Client-Id` header). **Decided:** the
  deterministic `TTSProvider`/`ASRProvider` implementations (called by
  Vaporware's core service on a fixed code path, e.g. an admin "speak
  this text" action) use the **REST API** directly — no need for an
  MCP session for a single deterministic call. The **MCP server** is
  the integration path for **agent-level access** — i.e. the Reasoning
  layer (or Claude Code, during development) calling VoiceBox as a
  tool it decides to use. Registered as a project MCP server in
  `.mcp.json` at the project root.

**Decided:** don't hand-roll individual engine integrations (Piper,
Kokoro, Chatterbox) one at a time — point `AudioActuator` at VoiceBox
as the default `TTSProvider` *implementation*, behind Vaporware's own
thin `TTSProvider` interface (not called directly), and get
engine-swapping (and several engines from the table above) for free.
VoiceBox's dictation feature is also the default `ASRProvider` behind
SoundObserver's transcription path — one integration covering both
the Audio Actuator and SoundObserver. If VoiceBox itself is ever
superseded, swapping it out is still just a config change on both
interfaces, which is the entire point of this pattern. Treat the
individual-engine survey above as the fallback path if VoiceBox
doesn't cover a future need (e.g. an ultra-constrained satellite node
that can't run the full app and just wants bare Piper).

**Complication as of the SoundObserver update:** SoundObserver now ships
*its own* TTS outputs directly — Apple Native TTS (`say`) and its own
VoiceBox TTS client (`/speak` → poll → `/audio`) — spoken whenever a
`tts` message lands on its own Spacebrew topic. That's a third TTS
integration surface alongside this doc's `TTSProvider` and
SoundObserver's ASR-side `VoiceBoxTranscriber`, all three talking to
the same underlying VoiceBox app independently. Not necessarily wrong
(SoundObserver may want to speak back locally without round-tripping
through Vaporware core's Reasoning layer for latency reasons) but worth
an explicit decision rather than three integrations growing apart by
accident — see the open question in `03-components.md`/
`04-actuators.md`.

Sources: [Best Local TTS Models 2026 — Local AI Master](https://localaimaster.com/blog/best-local-tts-models), [Kokoro vs XTTS vs Chatterbox — Local AI Master](https://localaimaster.com/blog/kokoro-vs-xtts-vs-chatterbox), [Local TTS & Voice Cloning Licenses 2026 — PromptQuorum](https://www.promptquorum.com/power-local-llm/local-tts-voice-cloning-piper-coqui-xtts), [Coqui TTS (XTTS-v2) 2026 — Local AI Master](https://localaimaster.com/models/coqui-tts), [Voicebox — Open Source Voice Cloning Desktop App](https://voicebox.sh/), [Voicebox Deep Dive — MindWiredAI](https://mindwiredai.com/2026/04/26/voicebox-the-free-local-elevenlabs-alternative-that-just-hit-22k-github-stars/)

### Prototype finding: `/transcribe` rejects webm/opus

Confirmed while building the first session prototype
(`vaporware-core/`): VoiceBox's `/transcribe` returns a 500 for
**any** webm/opus file — the browser `MediaRecorder` API's native
output — regardless of audio content (tested with both real speech
and pure silence, identical failure). The same audio re-encoded as
WAV transcribes correctly. The `ASRProvider`/browser client works
around this by capturing raw PCM via Web Audio and encoding WAV
client-side rather than using `MediaRecorder` directly. Worth
retesting if/when VoiceBox patches this.

## Generalizing beyond TTS

The same pattern applies wherever `03-components.md`/`04-actuators.md`
already said "off-the-shelf building blocks (candidates) — evaluate,
don't assume":

- **ASRProvider** (speech-to-text) — behind SoundObserver's
  transcription path (Whisper-class candidates). SoundObserver's own
  implementation has already outgrown "one Whisper-class candidate,"
  running VoiceBox STT and Apple's on-device `SFSpeechRecognizer` side
  by side as independently-switchable engines — a real instance of the
  Provider-swapping pattern this doc proposes, just not built as a
  single interface with a swap point (it's two parallel toggles, not
  one `ASRProvider` with an active implementation). Worth reconciling
  if/when this pattern gets formalized.
- **ImageProvider** / **VideoProvider** — behind DisplayActuator's
  generated-content path.
- Potentially the **local LLM(s)** in Reasoning itself, though that's
  a bigger swap than a single-capability Provider and may deserve its
  own doc later.

Same shape every time: stable interface, swappable Provider, registry
+ selection in the admin UI, license tracked per Provider.

## Open questions (to discuss)

- **Per-Ritual Provider selection** — does every Ritual share one
  active `TTSProvider`, or can a Ritual request one by capability hint
  (e.g. "low-latency" for an urgent alert vs. "cloned voice" for a
  bedtime-story Ritual)? The interface above assumes the latter is at
  least possible.
- **Where Providers run** — always on Homebase, or can a satellite/
  Travelbase/Wearable node run its own lightweight Provider (e.g.
  Piper) locally for latency, while Homebase handles higher-quality
  narration? Mirrors the "lighter/quantized local model" idea for
  Travelbase in `02-architecture.md`.
- **Voice cloning as a feature at all** — Chatterbox/XTTS v2 make
  cloning your own (or a family member's) voice plausible. Is that
  something you want Vaporware to do, or is a fixed set of "system
  voices" (Kokoro/Piper) preferable — cloning raises its own consent
  questions echoing the Observer privacy tiers in `03-components.md`.
- **License gating in the registry** — should the admin UI visibly
  flag non-commercial-only Providers (XTTS v2, F5-TTS) so a future
  decision to share/ship Vaporware doesn't quietly inherit a licensing
  problem?
- ~~VoiceBox integration depth~~ **Decided: thin wrapper.** Vaporware
  keeps its own `TTSProvider` interface; VoiceBox sits behind it as
  the default implementation, not called directly. Swapping it out
  later stays a config change.
- ~~VoiceBox as ASRProvider~~ **Superseded.** Originally decided as a
  second interface inside Vaporware core, sharing one integration with
  TTS. In practice, AudioObserver (now renamed **SoundObserver**) was
  extracted into its own project (`../VaporwareSoundObserver`) to match
  VisualObserver's satellite-node pattern — so the ASR-side VoiceBox
  integration (`VoiceBoxTranscriber`) now lives *there*, calling the
  same VoiceBox REST API independently. Vaporware core only keeps the
  `TTSProvider` side; it reaches SoundObserver's output via MQTT, not
  by calling VoiceBox for transcription itself. Two separate
  integrations to the same app, each owned by the project that
  actually uses it — now three, counting SoundObserver's own new TTS
  outputs (see above).

## Status

Draft v0, written 2026-07-03, updated 2026-07-11 for the AudioObserver
→ SoundObserver rename and its new independent TTS outputs. First
instance of the Provider pattern; cross-referenced from
`04-actuators.md` (AudioActuator) and intended as the template for
ASR/Image/Video providers later.
