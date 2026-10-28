# Verity — Public Offer Intelligence Platform

A professional, legal public-offer monitoring platform for AI tools, SaaS subscriptions, student programs, startup credits, and free-tier promotions.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)

## 🎯 Product Vision

Verity discovers, validates, and tracks legitimate public access programs without violating platform rules, scraping private account data, or automating around security protections.

The product helps users find real opportunities such as:

- AI model access trials (Claude, GPT-4, etc.)
- Free API credits and usage quotas
- Student or education access programs
- Startup and partner program credits
- Plan-based promotions and bundles
- Limited-time launch programs
- Public SaaS bundles and onboarding deals

The system focuses on **public, official, verifiable opportunities** and reduces noise by ranking offers by legitimacy, expiry risk, and user value.

## ✨ Key Features

### Advanced Agent System
- **Researcher Agents**: Discover leads across platforms (Reddit, GitHub, Hacker News, Product Hunt, Twitter/X)
- **Worker Agents**: Verify opportunities using real browser automation (Playwright)
- **Analyzer Agents**: Analyze trends, patterns, and insights from collected data
- **Orchestrator Engine**: Coordinates all agents, manages job queues, monitors performance
- **Agent Memory System**: Stores learnings and context for future reference
- **Real-time Monitoring**: WebSocket-based live dashboard updates

### Web Scraping & Browser Automation
- **Platform-specific integrations**: Reddit, GitHub, Hacker News, and more
- **Rate limiting**: Respectful API usage with per-platform rate limiters
- **Browser automation**: Playwright-based verification with screenshot capture
- **Content extraction**: Intelligent extraction of offers, eligibility info, and metadata
- **Form detection**: Automatic detection and analysis of signup forms

### Multi-Provider AI Support
- Anthropic (Claude 3 Haiku, Sonnet, Opus)
- OpenAI (GPT-4o, GPT-4o Mini)
- Groq (Llama 3 8B, 70B - free tier)
- Custom providers (extensible)
- Automatic failover between providers

### Security & Reliability
- Rate limiting and input validation
- URL validation and sanitization
- CORS hardening
- SQLite database with migrations
- Comprehensive error handling

## 🏗️ Architecture

### 1. Source Intake
The platform monitors official sources such as:

- Product pricing pages
- Launch blogs and documentation
- Partner announcements
- Student programs
- Startup credit portals
- Public newsletters
- Community platforms (Reddit, GitHub, etc.)

### 2. Offer Extraction
The engine detects program attributes such as:

- Type of offer (trial, credits, education, startup)
- Reward value and duration
- Restrictions and eligibility requirements
- Source URL and last-checked timestamp
- Expiry or renewal policy
- Verification confidence score

### 3. Validation Stage
Each offer is assessed on whether it is:

- Official and from a trusted source
- Current and still active
- Relevant to a user segment
- Likely to be valid and legitimate
- Restricted by region, identity, or plan tier

### 4. User Dashboard
A premium dashboard surfaces:

- Tracked programs and providers
- Active offers with confidence scores
- High-confidence recommendations
- Stale or monitoring-only entries
- Category filters and search
- Offer score and risk signals
- Real-time agent activity

## 🚀 Quick Start

### Prerequisites
- Python 3.12 or higher
- Git
- (Optional) API keys for AI providers (Anthropic, OpenAI, Groq)

### Installation

```bash
# Clone the repository
git clone https://github.com/mpaktit/Verity.git
cd Verity

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Initialize database
python -c "from app.db import init_db; init_db()"

# Run the application
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Access the Application

Open your browser to:
- **Dashboard**: http://localhost:8000/
- **API Health**: http://localhost:8000/api/health
- **API Documentation**: http://localhost:8000/docs

## 📖 API Reference

### Authentication

Most endpoints require authentication. Sign up and login to get a bearer token:

```bash
# Sign up
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name": "Your Name", "email": "you@example.com", "password": "securepassword"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "securepassword"}'
```

### Core Endpoints

#### Offers
```bash
# Get all offers
curl http://localhost:8000/api/offers

# Get summary statistics
curl http://localhost:8000/api/summary
```

#### Providers
```bash
# Get all providers
curl http://localhost:8000/api/providers

# Get provider details
curl http://localhost:8000/api/providers/{provider_id}
```

#### Research & Intelligence
```bash
# Get research status
curl http://localhost:8000/api/research

# Get alerts
curl http://localhost:8000/api/alerts

# Get insights
curl http://localhost:8000/api/insights

# Get analytics
curl http://localhost:8000/api/analytics
```

### Agent System Endpoints

#### Manage AI Keys
```bash
# Add API key
curl -X POST http://localhost:8000/api/ai/keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider": "anthropic", "key_name": "My Claude Key", "api_key": "sk-ant-..."}'

# List API keys
curl http://localhost:8000/api/ai/keys \
  -H "Authorization: Bearer YOUR_TOKEN"

# List available models
curl http://localhost:8000/api/ai/models \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Control Agents
```bash
# Start agent orchestrator
curl -X POST http://localhost:8000/api/agents/start \
  -H "Authorization: Bearer YOUR_TOKEN"

# Stop agent orchestrator
curl -X POST http://localhost:8000/api/agents/stop \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get agent status
curl http://localhost:8000/api/agents/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# Trigger manual research
curl -X POST http://localhost:8000/api/agents/research \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"platform": "reddit"}'

# List jobs
curl http://localhost:8000/api/agents/jobs \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get agent memory
curl http://localhost:8000/api/agents/memory \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get agent logs
curl http://localhost:8000/api/agents/logs \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### WebSocket

Connect to real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/agents');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log(message.type, message.data);
};
```

Available channels:
- `agents` - Agent status updates
- `jobs` - Job status updates
- `opportunities` - New opportunity discoveries
- `verifications` - Verification completions
- `alerts` - System alerts
- `metrics` - System metrics

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_agents.py
```

## 📊 Database Schema

The application uses SQLite with the following main tables:

- `workers` - User accounts and authentication
- `providers` - Platform/provider information
- `sources` - Monitored URLs and pages
- `offers` - Discovered opportunities
- `evidence` - Verification evidence
- `agent_jobs` - Agent task queue
- `agent_memory` - Agent learning storage
- `agent_logs` - Agent activity logs
- `api_keys` - AI provider API keys

See `app/migrate.py` for the full schema definition.

## 🔧 Configuration

Environment variables (optional):

```bash
# Database
DATABASE_URL=sqlite:///./data/verity.db

# CORS
CORS_ORIGINS=["http://localhost:8000", "http://127.0.0.1:8000"]

# Scheduler
VERITY_ENABLE_SCHEDULER=true
CRAWL_INTERVAL_SECONDS=3600

# Application
APP_VERSION=0.2.0
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📜 License

MIT License - see LICENSE file for details.

## 🛡️ Safety and Ethics

This platform is intentionally designed as a **public-offer intelligence system**. It does not attempt to:

- Bypass platform protections
- Scrape private data
- Impersonate users
- Automate restricted account flows
- Exploit access without consent

This makes it viable as a real product and safer for long-term use.

## 📞 Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/mpaktit/Verity/issues
- Documentation: See docs/ folder

## 🗺️ Roadmap

### Phase 1: Core Intelligence ✅
- Source listing and crawling
- Offer scoring engine
- Validation notes
- User watchlists

### Phase 2: Research Automation ✅
- Web scraping with platform integrations
- Browser automation for verification
- Real-time monitoring via WebSocket
- Job scheduling with APScheduler

### Phase 3: Verification Workflow (In Progress)
- Team review flows
- Post-validation approval states
- Evidence links and screenshots
- Manual confirmation architecture

### Phase 4: Advanced Intelligence (Planned)
- Alerts and notifications
- Saved search/watchlists
- Recommendation engine
- User segmentation by needs and budgets

### Phase 5: Enterprise Features (Planned)
- Multi-tenant support
- Advanced permissions
- API rate limiting per user
- Custom integrations
- White-label options
