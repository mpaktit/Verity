# Verity — Kilo Code Handoff

## 1) Project identity

Name: Verity

One-line product description:
A premium public-offer intelligence platform for tracking, validating, and reviewing legitimate free access, startup credits, student programs, partner offers, and AI/SaaS promotions that are public, official, and verifiable.

Intent:
This is not a hacking tool, exploit engine, or fake-account automation system. It is a serious research and verification product designed around public, legal, official, and user-safe monitoring workflows.

The product is meant to help people answer:
- What offers are actually public and visible?
- Which ones are real, official, and still active?
- What conditions or eligibility rules matter?
- Which programs are worth acting on, and which require caution?
- What is being monitored, reviewed, and scored across the ecosystem?

---

## 2) Product thesis and positioning

The original broad idea was: find ways to monitor AI and SaaS access opportunities, free tiers, partner statuses, startup offers, student programs, launches, pricing changes, and other signals across public sources.

The project was then intentionally refined into a more sensible and credible product direction:
- public-only intelligence
- official-source validation
- no bypass or private account logic
- no scraping of restricted/private data
- no fake user automation
- research + verification + scoring + review workflow

This is the product direction we committed to:
- marketable, premium, professional app
- serious workflow for research and verification
- credible UI/UX with light cream editorial tone
- modern SaaS product feel
- strong business value and research operational realism

The app is positioned as a trustworthy research desk for public offer intelligence, not as a loophole generator.

---

## 3) Core user value

Users want to know if an AI product, SaaS tool, education offer, or startup program is genuinely available, public, and worth trying.

This tool helps by organizing that research into:
- tracked offers
- provider coverage and research status
- signal summaries
- eligibility observations
- verification pipeline and review actions
- public confidence scoring
- monitoring and alerts

The app helps a user move faster and make better decisions without drowning in scattered sources.

---

## 4) Business / product framing

The product should feel like a premium software tool:
- clean, modern, confident
- credible and professional
- not AI-slop design
- light cream / editorial aesthetic
- premium copy and polished product language
- product could be marketed and sold
- has operational seriousness and trust signals

The user repeatedly pushed for wording and UI to feel more human-crafted, premium, and not generic.

The target feels like:
- serious platform
- research desk for public access intelligence
- SaaS-style dashboard with workflow and operational depth

---

## 5) Product constraints and ethics

This project is intentionally limited to:
- public information
- official sources
- public offer visibility
- eligibility and policy signals
- review logic and evidence tracking

It must not do:
- private account scraping
- fake identity creation
- credential abuse
- hidden account logic exploitation
- bypassing authentication or security systems
- automation aimed at circumventing platform restrictions

This is a positive product design decision and a long-term viability requirement.

---

## 6) Current project status

This repository already includes a working MVP / prototype with the following implemented:

- FastAPI backend
- static dashboard frontend
- auth flow with signup/login
- worker workspaces
- task submission and review workflow
- provider coverage cards
- public offer dataset
- alerts and insights endpoints
- analytics endpoints
- metrics and UI panels
- premium light theme direction
- regression tests

The codebase is in a stable state and already passes validation.

---

## 7) Tech stack

Backend:
- Python 3.12
- FastAPI
- Uvicorn

Frontend:
- HTML
- CSS
- vanilla JavaScript

Testing:
- pytest
- TestClient

Persistence:
- JSON-based worker store for current MVP
- future upgrade path to a real DB is recommended

Important environment note:
Python 3.14 caused dependency incompatibility issues. The project was standardized to Python 3.12 and is intended to remain there unless dependencies are upgraded deliberately.

---

## 8) Repository structure

Key files and purpose:

- README.md
  Project overview, framing, product principles, roadmap, setup

- app/main.py
  FastAPI app entry point, routes, auth handling, workspace endpoints

- app/services/research.py
  Core service logic for offers, providers, alerts, insights, analytics, worker auth, tasks, reviews

- app/data/offers.py
  Seed dataset for public offers and opportunities

- app/data/providers.py
  Provider metadata and monitoring coverage data

- app/data/alerts.py
  Alert feed and signal items

- app/static/index.html
  Single-page dashboard shell

- app/static/styles.css
  Premium visual design, layout, light theme, product polish

- app/static/app.js
  Frontend rendering, auth flow, task logic, modal detail views, verification interactions

- tests/test_api.py
  Regression tests for contracts and flows

- app/data/workers.json
  Current lightweight worker persistence store

---

## 9) Current implemented behavior

### Public dashboard
The app provides a landing dashboard with:
- summary cards
- provider coverage
- tracked offers
- alerts feed
- insights
- analytics
- search/filtering

### Worker system
Users can:
- sign up
- login
- access a workspace
- receive a verification task board
- submit attempts on tasks
- submit review decisions

### Review workflow
The workspace includes task records with:
- provider
- title
- summary
- signals
- attempts
- review state
- status progression

### Data model
Public offers are represented with fields such as:
- provider
- product
- category
- status
- reward
- eligibility
- source
- official vs unofficial
- verified flag
- score

Providers track:
- name
- status
- coverage percent
- source count
- signal summary
- notes

---

## 10) API surface

Important endpoints:

- GET /
  serves the app shell

- GET /api/health
  service health check

- GET /api/offers
  returns offer dataset

- GET /api/summary
  aggregated summary counts

- GET /api/providers
  returns provider list

- GET /api/providers/{provider_id}
  returns provider detail with related offers

- GET /api/research
  returns research monitoring status

- GET /api/alerts
  returns alert feed

- GET /api/insights
  returns summary and signal snapshot

- GET /api/analytics
  returns pipeline and monitoring trend data

- POST /api/auth/signup
  create user worker account

- POST /api/auth/login
  sign in worker

- GET /api/workspace
  returns profile and current workspace

- POST /api/workspace/attempt
  submit a verification attempt

- POST /api/workspace/review
  submit a review decision

---

## 11) Security and auth notes

The current app already includes stronger practices than the early stages:
- password hashing with PBKDF2 + salt
- secure token generation
- session verification via bearer token
- worker lookup by token

The app is still not production-grade for multi-user scale, but the auth layer is no longer simplistic or insecure.

Remaining gaps for later work:
- real DB instead of JSON storage
- stronger audit trails
- role management
- manager review workflows
- better session management
- production-ready secrets/config patterns

---

## 12) Product visual direction

The last push emphasized a more premium visual identity:
- light cream and warm neutral palette
- less neon/glow-heavy look
- subdued, editorial layout
- softer premium surfaces
- more polished and human design language
- crisp product copy and professional tone

The user explicitly rejected the earlier “ai-made slop” style and requested a calmer, more human-crafted product direction.

This is now the preferred look and tone: premium, warm, minimal, credible.

---

## 13) Current functional status

Validated working state:
- app starts successfully with Python 3.12
- FastAPI services respond
- frontend loads
- auth flow works in API contracts
- workspace flow works in API contracts
- attempt and review flow works
- regression suite passes

Evidence from project history:
- pytest result: 13 passed
- live homepage served successfully with updated content

---

## 14) Known issues / technical debt

These are the main things still worth improving before treating the product as production-grade:

1. JSON persistence is not enough for serious production use
   - workers.json should be replaced with SQLite/Postgres or a real service

2. No true monitoring automation
   - no live crawling or source ingestion engine yet

3. No real browser automation or verification pipeline
   - cannot yet track dynamic web states across sources

4. No advanced role management
   - team/manager reviewer flows not fully modeled

5. No long-term scheduling or background job system
   - monitoring tasks are still mocked or seeded

6. UI is polished but still bounded by demo data
   - looks credible, but the product is still a strong MVP rather than a real production intelligence engine

---

## 15) Next recommended priorities

Recommended order for the next engineer:

### Priority 1: persistence and backend hardening
- replace JSON worker store with SQLite/Postgres
- add schema migration approach
- centralize data models
- add better audit/logging

### Priority 2: real monitoring architecture
- add source registry
- add scheduled checks for public offers and provider states
- build scraper/ingestion layer for official public sources
- store evidence records and snapshots

### Priority 3: verification workflow expansion
- create richer review status states
- add evidence collection and attachments
- support manager approvals
- track reviewer decisions and notes

### Priority 4: product polish and brand consistency
- keep the light premium aesthetic intact
- fine-tune copy and interface language
- remove any generic dashboard feel
- strengthen marketing positioning and “serious tool” tone

### Priority 5: intelligence layer
- add offer scoring engine sophistication
- add confidence/risk logic
- make alerts more nuanced
- build recommendation and watchlist features

---

## 16) Exact execution guidance

When continuing the project, keep these design principles in mind:

- Keep the app public- and trust-oriented.
- Do not drift into exploitative or restricted workflows.
- Prefer official/public evidence, not private data.
- Keep the visual direction premium and human-crafted.
- Use serious, professional product language.
- Treat this as a real business-grade research/product tool.

---

## 17) Run commands

From the project root:

PowerShell:
```powershell
cd "d:\temp=garbage D\miko"
.\.venv\Scripts\Activate.ps1
python -m pytest -q
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open:
- http://127.0.0.1:8000/

If there is a stale uvicorn process on port 8000, kill old python/uvicorn instances before relaunching.

---

## 18) Summary for Kilo Code

This project is a premium public-offer intelligence platform called Verity.

It was evolved from a broad “AI/free access” concept into a legal, public, serious research platform that helps detect and verify public AI/SaaS access offers, monitor sources, and track offer confidence. It includes a working backend, frontend, worker workflow, auth, review pipeline, analytics, and a polished UX direction.

Kilo Code should treat this as a real product continuity task, not a toy app. The next work should focus on making it more production-ready while preserving the same serious, premium positioning.

---

## 19) Final note

The user’s explicit expectations throughout the chat were:
- continue until it is a serious, polished product
- premium UX/UI and strong product quality
- modern, human-crafted, not generic or AI-slop
- legal/public-facing and trustworthy
- work from task to task, thoughtfully and professionally
- maintain a real product feel with operational workflow and reasoning

Carry that forward.
