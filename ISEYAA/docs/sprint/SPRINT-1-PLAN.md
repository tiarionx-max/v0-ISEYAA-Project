# ISEYAA — Sprint 1 (Week 1–3) Engineering Plan
## Ogun State Digital Operating System — Phase 1 MVP Foundation
### Classification: Confidential | PRD v2.0 Reference

---

## Sprint Overview

| Attribute       | Detail                                      |
|-----------------|---------------------------------------------|
| Sprint Duration | 3 weeks (21 working days)                   |
| Objective       | Initialize platform scaffold, API Gateway, 3 core services live, AI agent framework |
| Teams           | Backend (4), Frontend (2), DevOps (1), AI/ML (1) |
| Definition of Done | Service passes tests, deployed to dev EKS, documented |

---

## Week 1 — Foundation & Infrastructure (Days 1–7)

### Day 1–2: Environment Setup
- [ ] Provision AWS af-south-1 via Terraform (VPC, EKS cluster, RDS, Redis, S3)
- [ ] Configure AWS Secrets Manager — all credentials migrated from .env.example
- [ ] Set up GitHub Actions CI/CD pipeline (lint → test → build → push to ECR)
- [ ] Configure Datadog APM + Sentry error tracking
- [ ] Docker Compose local dev environment validated by all engineers
- [ ] ArgoCD configured for GitOps deployment to EKS

**Owner:** DevOps  
**Acceptance:** `terraform apply` completes clean; all services reach `healthy` in compose

---

### Day 3–4: API Gateway + Auth Service
- [ ] API Gateway: FastAPI scaffold, JWT middleware, rate limiter, circuit breaker
- [ ] API Gateway: Route proxying to downstream services
- [ ] Auth Service: User registration, login, JWT issuance, refresh tokens
- [ ] Auth Service: KYC stub (NIN/BVN verification — mock in dev, real in staging)
- [ ] Auth Service: RBAC roles defined (citizen, vendor, athlete, government_officer, ministry_admin, super_admin)
- [ ] Auth Service: 2FA enforcement for financial and government routes
- [ ] PostgreSQL schema: users, sessions, roles tables + Alembic migration

**Owner:** Backend Team A  
**Acceptance:** POST /api/v1/auth/register → JWT; secured routes reject invalid tokens

---

### Day 5–7: Wallet Service Scaffold
- [ ] Wallet Service: PostgreSQL schema (wallets, transactions, escrow) in isolated DB
- [ ] Wallet Service: Wallet creation on user registration (event-driven via SQS)
- [ ] Wallet Service: Paystack initialize + verify transaction endpoints
- [ ] Wallet Service: Webhook handler (HMAC-SHA512 verified)
- [ ] Wallet Service: IGR split calculation engine (configurable % to OGIRS)
- [ ] Wallet Service: Basic wallet balance API

**Owner:** Backend Team B  
**Acceptance:** Test payment flow end-to-end on Paystack sandbox

---

## Week 2 — Core Services (Days 8–14)

### Day 8–10: Events Service
- [ ] Events Service: PostgreSQL + MongoDB schema (events, ticket_tiers, tickets, venues)
- [ ] Events Service: CRUD endpoints for event creation
- [ ] Events Service: Government approval workflow (draft → pending_approval → approved → published)
- [ ] Events Service: Ticket tier creation with pricing rules
- [ ] Events Service: QR code generation on ticket purchase (via qrcode library)
- [ ] Events Service: Paystack integration for ticket payment

**Owner:** Backend Team A  
**Acceptance:** Create event → approve → purchase ticket → scan QR → checked_in=true

---

### Day 11–12: LGA Intelligence Service
- [ ] LGA Intelligence Service: ClickHouse schema for analytics events
- [ ] LGA Intelligence Service: IGR summary, by-module, by-LGA endpoints
- [ ] LGA Intelligence Service: Redis caching layer (5-min TTL)
- [ ] LGA Intelligence Service: Role-based access (government_officer minimum)
- [ ] LGA Intelligence Service: Real-time metrics endpoint (last 24h)

**Owner:** Backend Team B  
**Acceptance:** IGR summary returns structured JSON; non-government roles receive 403

---

### Day 13–14: AI Layer — Orchestrator + LGA Agent
- [ ] AI Layer: OrchestratorAgent with Claude API integration
- [ ] AI Layer: LGAIntelligenceAgent — IGR report, LGA comparison, ministry dashboard
- [ ] AI Layer: EventsAgent — AI event setup (pre-fill schedule, venue, bracket)
- [ ] AI Layer: Task queue with asyncio Semaphore (max 5 concurrent AI calls)
- [ ] AI Layer: Audit trace for all AI decisions (government-grade)
- [ ] AI Layer: FastAPI wrapper exposing /api/v1/ai/* endpoints

**Owner:** AI/ML Engineer  
**Acceptance:** POST /api/v1/ai/lga/igr-report returns structured JSON; trace logged

---

## Week 3 — Integration, Frontend & Hardening (Days 15–21)

### Day 15–16: Frontend Scaffold
- [ ] Next.js 14 app with App Router, TypeScript strict mode
- [ ] Shadcn/UI + Tailwind CSS design system with ISEYAA brand tokens
- [ ] next-i18next: English, Yoruba, Hausa configured
- [ ] React Query + Zustand state management
- [ ] Authentication flow: login, register, JWT refresh
- [ ] Citizen portal: basic dashboard, wallet balance, events listing
- [ ] Government dashboard: IGR summary cards (live data from LGA service)

**Owner:** Frontend Team  
**Acceptance:** Citizens can register, view wallet; government officers see IGR dashboard

---

### Day 17–18: React Native / Expo Mobile Scaffold
- [ ] Expo project with TypeScript
- [ ] Navigation: React Navigation 6 (tab + stack)
- [ ] Auth screens: login, register, OTP verification
- [ ] Wallet screen: balance, topup CTA
- [ ] Events listing + ticket purchase screen
- [ ] FCM push notification integration
- [ ] Offline storage: AsyncStorage for auth token

**Owner:** Frontend Team  
**Acceptance:** App runs on iOS simulator and Android emulator with login flow complete

---

### Day 19–20: Integration Testing & Security
- [ ] End-to-end test: register → add funds → purchase event ticket → scan at gate
- [ ] Webhook tests: Paystack payment confirmed → wallet credited → IGR recorded
- [ ] AWS WAF rules validated (OWASP managed ruleset)
- [ ] Rate limiting verified under load (k6 load test)
- [ ] JWT expiry and refresh flow tested
- [ ] 2FA enforcement on wallet transfer verified
- [ ] Dependency vulnerability scan (Snyk)

**Owner:** All Teams  
**Acceptance:** All integration tests pass; no HIGH/CRITICAL CVEs in pipeline

---

### Day 21: Documentation & Sprint Review
- [ ] OpenAPI docs reviewed and published (internal)
- [ ] Architecture Decision Records (ADRs) for key choices
- [ ] Runbook: local setup, deployment, incident response
- [ ] Sprint retrospective
- [ ] Backlog grooming for Sprint 2 (Transport, Sports, HMO modules)

---

## Key Architectural Decisions (ADRs)

### ADR-001: FastAPI for AI/Python Services
**Decision:** Python FastAPI for AI layer and analytics services, aligned with user specification.  
**Context:** PRD §5.1 specifies NestJS as primary. Resolution: FastAPI serves as the AI/Python microservice layer (ai-layer, lga-intelligence-service) while NestJS handles remaining services in Sprint 2+.  
**Status:** Accepted

### ADR-002: PostgreSQL as Primary Transaction Store
**Decision:** PostgreSQL (RDS Multi-AZ) for all ACID-critical data.  
**Rationale:** PRD §5.5 mandates full ACID compliance for wallets, payments, users.  
**Status:** Accepted

### ADR-003: Isolated Wallet Database
**Decision:** Separate RDS instance for Wallet Service.  
**Rationale:** Financial data isolation, independent backup policy (90 days), and independent scaling.  
**Status:** Accepted

### ADR-004: Claude API as Orchestrator Brain
**Decision:** Anthropic Claude Opus 4 for all LLM inference in the orchestrator.  
**Rationale:** PRD §4.8 specifies Claude API; superior reasoning for government-grade decisions.  
**Status:** Accepted

### ADR-005: AWS af-south-1 Primary Region
**Decision:** All workloads primary in Cape Town; DR in eu-west-1.  
**Rationale:** PRD §5.4 — minimum latency to Nigerian users; NDPA data residency on African continent.  
**Status:** Accepted

---

## Sprint 2 Preview (Weeks 4–6)
- Transport module: ride-hailing, driver app, live tracking (Ably)
- Sports management: leagues, scheduling, athlete registry
- HMO: subscription, appointment booking, claims
- NestJS services migration/addition
- Flutter mobile app (replaces Expo for production)
- Flutterwave secondary gateway

## Sprint 3 Preview (Weeks 7–9)
- Media Intelligence Agent (Claude API news summarisation)
- AI Itinerary Planner (Claude + Google Maps)
- Citizen AI Chatbot (Yoruba/Hausa/English)
- Fraud detection rule engine
- AR/VR Phase 3 spike

---

*Sprint plan aligned with PRD v2.0 Phase 1 (Months 1–4) objectives.*  
*All deviations from PRD require written CTO approval per §10 Success Criteria.*
