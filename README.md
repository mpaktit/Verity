    # Verity — public offer intelligence

A professional, legal public-offer monitoring platform for AI tools, SaaS subscriptions, student programs, startup credits, and free-tier promotions.

This project is designed around a real-world use case: discovering, validating, and tracking legitimate public access programs without violating platform rules, scraping private account data, or automating around security protections.

## Product vision

The product helps users find real opportunities such as:

- AI model access trials
- free API credits
- student or education access
- startup and partner programs
- plan-based promotions
- limited-time launch programs
- public SaaS bundles and onboarding deals

The system focuses on public, official, verifiable opportunities and reduces noise by ranking offers by legitimacy, expiry risk, and user value.

## Why this matters

Many users want access to premium AI and productivity tools but do not have the time to monitor every official announcement, pricing page, newsletter, education program, or startup offer. This tool centralizes that research and helps the user act faster with better decision-making.

## Core principles

- Public-only monitoring
- Official source validation
- No fake accounts or bypass techniques
- Clear eligibility analysis
- Real scoring and trust signals
- Dashboard-level visibility for active opportunities

## Product architecture

### 1. Source intake
The platform monitors official sources such as:

- product pricing pages
- launch blogs
- docs pages
- partner announcements
- student programs
- startup credit portals
- public newsletters

### 2. Offer extraction
The engine detects program attributes such as:

- type of offer
- reward value
- restrictions and eligibility
- source URL
- expiry or renewal policy
- verification confidence

### 3. Validation stage
Each offer is assessed on whether it is:

- official
- current
- relevant to a user segment
- likely to be valid
- likely to be restricted by region, identity, or plan tier

### 4. User dashboard
A dashboard surfaces:

- tracked programs
- active offers
- high-confidence recommendations
- stale or monitoring-only entries
- category filters
- offer score and risk signal

### 5. AI-powered agent system (NEW)
The platform now includes autonomous subagents for research and verification:

- **Researcher Agents**: Discover leads across platforms (Twitter, Reddit, GitHub, Product Hunt, Hacker News)
- **Worker Agents**: Verify opportunities, check eligibility, gather evidence
- **Analyzer Agents**: Analyze trends, patterns, and insights from collected data
- **Orchestrator Engine**: Coordinates all agents, manages job queues, monitors performance
- **Multi-Provider AI Support**: Supports Anthropic, OpenAI, Groq, and other providers with automatic failover
- **Agent Memory System**: Stores learnings and context for future reference
- **Real-time Monitoring**: Dashboard shows agent activity, job queue, and logs in real-time

## MVP status

This repository contains a working MVP with:

- a FastAPI backend
- a dashboard UI
- a public offers dataset
- summary statistics
- health checks and API endpoints
- a product architecture aligned to real-world use

## Roadmap

### Phase 1: Core intelligence
- add source listing and crawling
- add offer scoring engine
- add validation notes
- add user watchlists

### Phase 2: Research automation
- crawl public pricing pages and official docs
- extract offers from structured and semi-structured sources
- track changes over time

### Phase 3: Verification workflow
- team review flows
- post-validation approval states
- evidence links and screenshots
- manual-confirmation architecture

### Phase 4: Advanced intelligence
- alerts and notifications
- saved search/watchlists
- recommendation engine
- user segmentation by needs and budgets

### Phase 5: Agent automation (NEW)
- autonomous research across platforms
- AI-powered verification and analysis
- multi-provider API key management
- real-time agent monitoring dashboard
- agent memory and learning system

## Local development

```bash
cd "d:\temp=garbage D\miko"
python -m venv .venv
. ./.venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# optional background scanning of official public pages
$env:VERITY_ENABLE_SCHEDULER = "true"
```

Then open:

- http://localhost:8000/
- http://localhost:8000/api/health
- http://localhost:8000/api/offers

## Agent system setup

To use the AI-powered agent system:

1. Add API keys via the Agents tab in the dashboard or via API:
   ```bash
   curl -X POST http://localhost:8000/api/ai/keys \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"provider": "anthropic", "key_name": "My Claude Key", "api_key": "sk-ant-..."}'
   ```

2. Start the agent orchestrator:
   ```bash
   curl -X POST http://localhost:8000/api/agents/start \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. Monitor agent activity on the Agents dashboard tab

4. Trigger manual research:
   ```bash
   curl -X POST http://localhost:8000/api/agents/research \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"platform": "twitter"}'
   ```

Supported AI providers:
- Anthropic (Claude 3 Haiku, Sonnet, Opus)
- OpenAI (GPT-4o, GPT-4o Mini)
- Groq (Llama 3 8B, 70B - free tier)
- Custom providers (extensible)

## Safety and ethics

This platform is intentionally designed as a public-offer intelligence system. It does not attempt to:

- bypass platform protections
- scrape private data
- impersonate users
- automate restricted account flows
- exploit access without consent

That makes it much more viable as a real product and much safer for long-term use.
