# Access Intelligence Platform — Product and Research Plan

## 1. Product definition

This project is a public intelligence and verification platform for discovering legitimate access offers for AI tools, SaaS services, student programs, free-tier promotions, and startup credits.

The app does not rely on fake identities, scraping private account pages, or bypassing platform protections. It focuses on public, official, and verifiable opportunities.

## 2. Core business value

Users want premium tools, but they do not have time to monitor:

- product pricing pages
- official announcements
- launch blogs
- newsletter drops
- education and startup programs
- community posts that reveal temporary access
- expired or changed offers

The platform centralizes this research and reduces the signal-to-noise problem.

## 3. Research model

The system should look at multiple research channels:

### Official channels
- company pricing and product pages
- docs and changelogs
- official blogs and release notes
- education program pages
- startup and partner pages
- public announcement portals

### Public community channels
- Reddit threads and discussions
- X posts and public threads
- Discord announcements and community channels
- public launch posts
- community-run trackers

### Hidden or trigger-based surfaces
- login-gated pricing sections
- user-dependent plan conditions
- account state dependent discounts
- referral pages
- college or workspace program pages
- partner bundle announcements

These require verification, not exploitation.

## 4. Data model

### Provider
- id
- name
- category
- website
- official status
- active research status

### Source
- id
- provider_id
- source_type
- url
- last_checked_at
- status

### Offer
- id
- provider_id
- title
- offer_type
- reward_summary
- eligibility_summary
- official
- active
- verified
- source_url
- score
- risk_level
- expires_at
- created_at
- updated_at

### Research Run
- id
- provider_id
- triggered_at
- source_count
- findings
- confidence

### Evidence
- id
- offer_id
- source_url
- screenshot_url
- note
- validated_by

## 5. Offer scoring model

Each offer receives a score from 0 to 100 using factors such as:

- official source confidence
- current status
- eligibility clarity
- user segment fit
- expiry and renewal risk
- community confirmation
- verification evidence

Example logic:

- official page + clear terms + active = 90+
- unofficial community-only mention = 50-70
- expired or unclear = below 50
- login-gated without public proof = review required

## 6. Research workflow

1. Discover sources for a provider or category.
2. Fetch public pages and parse content.
3. Extract likely offers and conditions.
4. Add them to a normalized offer record.
5. Score reliability and confidence.
6. Validate against official sources.
7. Store evidence and human notes.
8. Surface alerts to the dashboard.

## 7. Safety principles

This platform is intentionally designed as a public research and verification system.

It must avoid:

- scraping private or account-protected pages
- impersonation or fake account flows
- anti-bot circumvention
- access abuse or bypassing paywalls
- private user data collection

The goal is to track and validate real public access, not to break access controls.

## 8. UI/UX needs

The app should feel premium and trustworthy.

### Core screens
- Overview dashboard
- Active offers
- Search and filters
- Provider intelligence
- Verification queue
- Saved watchlists
- Trend over time
- Alerts center

### UX qualities
- fast scanning
- high-confidence badges
- visual trust scoring
- clear explanation of rules and restrictions
- dark, premium SaaS-style design

## 9. Recommended next build steps

### Phase 1
- working dashboard
- offer model and API
- seed source list
- public research flow

### Phase 2
- browser automation for verification
- source monitoring jobs
- scoring logic and alerts
- UI filters and search

### Phase 3
- AI summarization layer
- provider intelligence and comparisons
- saved searches and notifications

### Phase 4
- user login and watchlists
- API integrations for alerts
- export and reporting
- premium subscription tiers

## 10. Long-term product vision

This product can grow into a market-worthy intelligence SaaS for creators and teams who need to know where real free or low-cost access is available.

It can also expand beyond AI tools into:

- design tools
- development tools
- productivity software
- startup programs
- education-based access
- cloud credits
- API free-tier monitoring
