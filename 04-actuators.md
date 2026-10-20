# Vaporware — Component Catalog: Actuators (draft v0)

The output/action mirror of `03-components.md`. If Observers turn raw
signal into meaning, Actuators turn a decision into a real-world
effect:

```
decision/content (from Reasoning) → [Actuator: rendering/execution] → real-world effect
```

## Two axes, not one list

Your list — robotic movement, text, image, video, audio, music, sound,
lights, media curation, interface screens, 3D prints, prints — mixes
two different concerns. Worth separating so we don't build one
Actuator per noun:

- **Content** — *what* is produced or selected: text, image, video,
  audio, music, sound effects. This is a Reasoning-layer concern
  (generation or selection), not a physical output.
- **Delivery surface** — *where* it lands in the physical/digital
  world: a screen, a speaker, a light, a printer, a 3D printer, a
  robot's motors, a sent message. This is the actual Actuator — the
  hardware/software endpoint content gets rendered through.

**Media curation is Reasoning, not an Actuator.** Deciding *what* to
play/show next from an existing library (music, photos, video) is a
selection/planning task — it produces content that then goes through
whichever delivery surface (AudioActuator, DisplayActuator) renders
it. It doesn't need its own physical endpoint.

A given delivery surface often carries multiple content types (a
screen shows text *and* image *and* video; a speaker plays speech
*and* music *and* alerts) — that's exactly why splitting by surface
instead of by content type keeps the count of Actuators manageable.

## Risk/reversibility tier (mirrors Privacy tier, feeds Governance)

| Tier | Meaning | Example |
|---|---|---|
| R1 — Trivial | Instantly reversible, no resource cost | Lights, screen content |
| R2 — Contained cost | Uses power/attention but stays local, no lasting artifact | Audio/video playback, ambient display |
| R3 — Consequential | Costs real material/time, leaves the system, or affects the physical/social world irreversibly | Printing, 3D printing, robotic movement, sending a message to a person |

R3 actions are exactly the ones that should require the highest
autonomy threshold from Governance (`02-architecture.md`) — start
suggest-only/confirm-before-acting, especially for anything that moves
in physical space or reaches another person.

## Actuators (delivery surfaces)

### DisplayActuator
Screens and ambient displays. Renders text, image, video, and
generated UI. Ranges from a full dashboard to a small ambient e-ink
panel. **Content it carries:** text, image, video. **Risk tier:** R1.
**Base:** any (Homebase dashboards, Travelbase laptop screen, wearable
watch face).

### AudioActuator
Speakers/sound output. Renders speech (TTS), music, and sound
effects/alerts. Mirrors SoundObserver on the input side — though that
mirror is no longer clean: SoundObserver (`03-components.md`) now ships
its own TTS outputs (Apple Native TTS, VoiceBox TTS) triggered over its
own Spacebrew `tts` topic, independent of this Actuator. Open question
carried over from `03-components.md`: does `AudioActuator` delegate to
SoundObserver's outputs, or do the two paths stay separate? **Content:**
audio, music, sound. **Risk tier:** R1 (alert) to R2 (sustained
playback). **Base:** any with speakers.

### LightActuator
Smart lighting — color, scene, signal. The lowest-bandwidth "display":
a single color/brightness change can encode a lot (presence, alert,
mood) without competing for attention like a screen does. **Risk
tier:** R1. **Base:** Homebase (fixed home lighting); portable smart
lights conceivable on Travelbase.

### MotionActuator
Robotic movement — servos, motors, robot arms/bases. The only Actuator
that acts directly in physical space with force behind it. **Risk
tier:** R3 — the highest-consequence Actuator by far: it's the one
that can cause physical damage or safety issues, and needs hard limits
/ a kill switch / explicit confirmation before autonomous use, not
just a policy flag. **Base:** Homebase-only for now (stationary
robotics); this is also the natural home for the "bidirectional
Controls" question raised in `03-components.md` — a motorized dial is
a MotionActuator wearing a Controls hat.

### PrintActuator
2D prints — documents, photos, physical paper output. **Content:**
text, image. **Risk tier:** R3 (consumes paper/ink, produces a
physical artifact you didn't necessarily ask for) but low-severity
compared to MotionActuator. **Base:** Homebase.

### FabricationActuator
3D prints — physical objects. **Content:** a 3D model (itself possibly
AI-generated). **Risk tier:** R3 — real material and meaningful time
cost per action; probably the Actuator most in need of an explicit
"confirm before starting a print" gate for a long while. **Base:**
Homebase.

### (Messages — already covered, not a new Actuator)
Sending messages / editing calendars / creating tasks were already
named in `02-architecture.md`'s Actuation layer. For naming
consistency you could call this a `MessageActuator`, but it's
existing scope, not new — flagging only so the family stays complete.
**Risk tier:** R3 — reaching another person can't be unsent.

## Comparison

| | Display | Audio | Light | Motion | Print | Fabrication |
|---|---|---|---|---|---|---|
| Content carried | text, image, video | speech, music, sound | color/scene | physical motion | text, image | 3D model |
| Risk tier | R1 | R1–R2 | R1 | **R3 (highest)** | R3 | R3 |
| Physical artifact left behind? | No | No | No | Possibly (side effects) | Yes (paper) | Yes (object) |
| Base | Any | Any | Mostly Homebase | Homebase only | Homebase | Homebase |
| Needs explicit confirm gate first? | No | No | No | **Yes, always at first** | Probably | Probably |

## Open questions (to discuss)

- **Generation vs. curation as a shared Reasoning capability** — text/
  image/video/music generation (new content) and media curation
  (selecting existing content) both feed the same Actuators. Worth
  designing as one "content pipeline" in Reasoning rather than
  per-Actuator logic?
- ~~MotionActuator safety model~~ **Decided: no special model for
  now.** It shares Governance's normal R1–R3 rules like every other
  Actuator, just tagged R3 — no separate permission system yet.
  Revisit once an actual MotionActuator is being built.
- **PrintActuator/FabricationActuator waste** — should these always
  require confirmation, or can some low-stakes cases (e.g. printing a
  boarding pass) be auto-approved once trust is established?
- ~~Do LightActuator and DisplayActuator overlap at the low end?~~
  **Decided: kept separate.** Even though a status light is
  low-bandwidth like a display, they stay distinct Actuators.

## Status

Draft v0, written 2026-07-03. Cross-references: `01-taxonomy.md`
(which domains act through which surface), `02-architecture.md`
(Actuation layer + Governance autonomy levels), `03-components.md`
(Observers/Controls — the input mirror of this doc).
