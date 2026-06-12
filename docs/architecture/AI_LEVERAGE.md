---
description: 'Copilot leverage model for GoblinOS Assistant — schema-driven engineering and boilerplate automation'
---

# AI Leverage Model

GoblinOS Assistant should treat AI as a force multiplier for **pattern-shaped correctness**: work that is repetitive, convention-heavy, locally deterministic, and easy to validate.

This document defines where AI should dominate, where humans must stay in control, and how to structure the repo so AI produces better output over time.

## 1. Core Principle

AI is strongest when the task already has a recognizable shape.

That means it excels at work with:

- predictable inputs and outputs
- repeated conventions
- known libraries and frameworks
- obvious plumbing
- a target pattern already present elsewhere in the repo

That is the repo’s "boilerplate destruction" zone.

## 2. What AI Should Own

Use AI for work that is low in business judgment and high in repetition:

- DTOs and shared types
- validation schemas
- CRUD endpoints and service scaffolding
- API wrappers and adapters
- test scaffolding and fixture generation
- form wiring and repetitive UI state handling
- config parsing and environment plumbing
- mechanical refactors and interface migrations
- docs that mirror stable implementation patterns

## 3. What Humans Should Own

Keep humans on the work with real tradeoffs and long-term consequences:

- architecture and subsystem boundaries
- domain modeling and invariants
- security boundaries and permission systems
- orchestration and failure semantics
- concurrency and retry strategy
- billing, routing, and cost policy
- data ownership and lifecycle design
- product logic that needs judgment

If AI is allowed to invent these too early, the repo can become locally correct but globally cursed.

## 4. Make the Repo Easy for AI to Help

AI output improves when the repo is structured around stable contracts and repeatable conventions.

Prefer:

- contract-first design
- shared schemas and typed boundaries
- feature-local API adapters
- consistent folder conventions
- one obvious way to do common tasks
- examples close to the abstractions they define
- explicit names that describe intent

This aligns with the existing architecture rules around typed contracts, clear boundaries, and orchestration-ready design.

## 5. Golden Path for Schema-Driven Engineering

The ideal workflow is:

1. define the contract
2. generate types and validators
3. derive SDKs and API adapters
4. build UI forms and CRUD plumbing from the contract
5. generate tests and mocks from the same source of truth

In practice, this means a change to one contract can update:

- Pydantic models
- TypeScript types
- API clients
- form validators
- event payloads
- test fixtures
- documentation

## 6. Repo Signals That Improve AI Output

AI performs better when the repo already contains:

- clear naming conventions
- repeatable request/response envelopes
- shared contracts in one place
- existing examples of the target pattern
- small, focused modules
- low coupling between UI, orchestration, and transport layers

AI performs worse when the repo contains:

- duplicated business logic
- hidden side effects
- vague helpers and utility dumps
- inconsistent file layouts
- untyped JSON blobs passed around freely
- one-off exceptions that bypass the normal flow

## 7. Practical Rule of Thumb

If a task is mostly:

- repetitive
- convention-based
- easy to validate
- already expressed elsewhere

then AI should probably do it.

If a task requires:

- judgment
- tradeoffs
- system design
- risk management
- security reasoning

then a human should lead.

## 8. Short Version

**Humans choose the structure. AI renders the structure.**

That is the operating model that makes GoblinOS Assistant faster without making it fragile.
