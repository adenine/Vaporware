# Vaporware — Vision (draft v0)

## One-liner

A local-first AI operating layer that senses and acts across the full
surface of your life — not one app, but a substrate that wires together
off-the-shelf tools and custom glue, coordinated by local AI with
persistent memory of *you*, so it can both **capture** (sense, log,
remember) and **act** (automate, suggest, execute) on your behalf.

## What problem this solves

Today the systems that touch your life are fragmented and dumb relative
to each other: your calendar doesn't know your health tracker, your
smart home doesn't know your calendar, your notes app doesn't know your
relationships, and nothing remembers *why* any of it matters to you.
Each vendor silo captures a thin slice and does nothing with the rest.

Vaporware is the connective tissue: a personal context layer plus an
orchestration layer that lets AI models act as agents *for you*, across
all these silos, grounded in an actual model of your life rather than
one API's slice of it.

## Design tenets (draft — confirm/argue)

1. **Local-only, privacy-preserving.** All compute, inference, and
   storage runs on hardware you own — no third-party cloud dependency
   for core function, not even as a fallback. A self-hosted relay node
   (a box or VPS you control, used purely to reach Homebase remotely)
   is fine; a third-party cloud LLM/API in the critical path is not.
2. **Loosely coupled, not a monolith.** Off-the-shelf where it's good
   enough; custom only where it isn't. Components should be swappable —
   this is a system of adapters, not a rewrite of everything.
3. **Capture before you act.** A memory/context substrate has to exist
   before actuation is trustworthy — automation without context is just
   scripts, not orchestration.
4. **Organized around the person, not the tech.** The taxonomy is your
   life (self, environment, people, stuff, stories, digital life), not
   "integrations" or "APIs."
5. **Progressive autonomy.** Start observational and suggestive; earn
   the right to act autonomously in a given domain over time, with
   visible permissions and an audit trail.

## Non-goals (draft)

- Not a single consumer app or product to ship to strangers (at least
  not yet) — this is being designed for one household/person first.
- Not trying to replace every off-the-shelf tool — the goal is
  orchestration and memory, not reinventing calendars or smart-home
  hubs.
- Not fully autonomous out of the gate — action-taking is earned, not
  assumed.

## Status

Draft v0, written 2026-07-03. Nothing below this doc is settled — see
`01-taxonomy.md` and `02-architecture.md` for the working sketches.
