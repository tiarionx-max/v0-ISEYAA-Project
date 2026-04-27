# ISEYAA
## Integrated State Experience, Economy & Automation Platform
### Ogun State Digital Operating System

[![Status](https://img.shields.io/badge/Status-Sprint%201%20Active-green)](docs/sprint/SPRINT-1-PLAN.md)
[![Classification](https://img.shields.io/badge/Classification-Confidential-red)](#)
[![PRD](https://img.shields.io/badge/PRD-v2.0%20Approved-blue)](#)

---

## Overview

ISEYAA is Ogun State Government's unified digital super-platform serving 7 million+ citizens, vendors, athletes, tourists, and government ministries through a single cloud-native ecosystem.

**The platform provides:**
- Citizen super-app (wallet, events, transport, marketplace, HMO)
- Government digital operations (IGR tracking, ministry dashboards, AI intelligence)
- State revenue optimisation engine
- AI-powered automation and multi-agent intelligence system

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ISEYAA Platform                           │
│                                                              │
│  ┌──────────┐   ┌──────────┐                                │
│  │  Next.js │   │  React   │  ← Frontend (Web + Mobile)    │
│  │   Web    │   │  Native  │                                │
│  └────┬─────┘   └────┬─────┘                                │
│       └──────┬────────┘                                     │
│              ▼                                               │
│  ┌───────────────────────┐                                  │
│  │     API Gateway       │  ← FastAPI + JWT + Rate Limiter  │
│  │   (Port 8000)         │                                  │
│  └───────┬───────────────┘                                  │
│          │ routes to:                                        │
│  ┌───────┴────────────────────────────────────┐            │
│  │              Microservices                  │            │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────┐ │            │
│  │  │  Auth    │ │  Wallet  │ │  Events    │ │            │
│  │  │ :8001    │ │  :8002   │ │   :8003    │ │            │
│  │  └──────────┘ └──────────┘ └────────────┘ │            │
│  │  ┌────────────────┐ ┌───────────────────┐  │            │
│  │  │ LGA Intel      │ │  Notifications    │  │            │
│  │  │   :8004        │ │     :8005         │  │            │
│  │  └────────────────┘ └───────────────────┘  │            │
│  └────────────────────────────────────────────┘            │
│          │                                                   │
│  ┌───────▼───────┐   ┌─────────────────────────┐          │
│  │   AI Layer    │   │    Data Layer            │          │
│  │  Orchestrator │   │  PostgreSQL (RDS)        │          │
│  │  LGA Agent    │   │  Redis (ElastiCache)     │          │
│  │  Events Agent │   │  MongoDB Atlas           │          │
│  │  Fraud Agent  │   │  ClickHouse (Analytics)  │          │
│  │    :8010      │   │  AWS SQS/SNS             │          │
│  └───────────────┘   └─────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Gateway + AI Services | Python 3.12 / FastAPI |
| Primary Backend Services | Python 3.12 / FastAPI (Sprint 1) → NestJS (Sprint 2+) |
| Financial Core | Python FastAPI (isolated wallet service) |
| Web Frontend | Next.js 14 (App Router) + TypeScript |
| Mobile (Dev) | React Native / Expo |
| Mobile (Production) | Flutter (Sprint 2) |
| Primary Database | PostgreSQL 16 (AWS RDS Multi-AZ) |
| Cache / Sessions | Redis 7 (AWS ElastiCache) |
| Analytics (OLAP) | ClickHouse |
| Document Store | MongoDB Atlas |
| AI / LLM | Anthropic Claude Opus 4 |
| Cloud | AWS af-south-1 (Cape Town) |
| Container Orchestration | Kubernetes (AWS EKS) |
| IaC | Terraform |
| CI/CD | GitHub Actions + ArgoCD |
| Observability | Datadog + Sentry |

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 20+
- AWS CLI configured

### 1. Clone and configure
```bash
git clone https://github.com/ogunstate/iseyaa.git
cd iseyaa
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY, PAYSTACK_SECRET_KEY, JWT_SECRET_KEY
```

### 2. Start infrastructure
```bash
docker compose up postgres postgres-wallet redis mongodb clickhouse -d
```

### 3. Run migrations
```bash
cd services/auth-service && alembic upgrade head && cd ../..
cd services/wallet-service && alembic upgrade head && cd ../..
cd services/events-service && alembic upgrade head && cd ../..
```

### 4. Start all services
```bash
docker compose up -d
```

### 5. Verify
```bash
curl http://localhost:8000/api/v1/health
# Expected: {"status": "healthy", "services": {...}}
```

**API Docs:** http://localhost:8000/docs (development only)

## Project Structure

```
iseyaa/
├── api-gateway/              # FastAPI API Gateway (port 8000)
├── services/
│   ├── auth-service/         # Identity & KYC (port 8001)
│   ├── wallet-service/       # Payments & IGR (port 8002)
│   ├── events-service/       # Events & Ticketing (port 8003)
│   ├── lga-intelligence-service/  # Gov Dashboard (port 8004)
│   └── notifications-service/    # SMS/Email/Push (port 8005)
├── ai-layer/                 # Multi-Agent System (port 8010)
│   └── agents/
│       ├── orchestrator/     # Central AI coordinator
│       ├── lga/              # Government analytics agent
│       ├── events/           # Event setup agent
│       ├── fraud/            # Fraud detection agent
│       ├── media/            # News intelligence agent
│       └── itinerary/        # Tourism planner agent
├── frontend/
│   ├── web/                  # Next.js citizen & government portals
│   └── mobile/               # React Native / Expo app
├── infrastructure/
│   ├── terraform/            # AWS infrastructure as code
│   ├── k8s/                  # Kubernetes manifests
│   └── docker/               # Docker configs
├── shared/                   # Shared schemas, utils, event types
├── docs/
│   ├── adr/                  # Architecture Decision Records
│   ├── sprint/               # Sprint plans
│   └── api/                  # API documentation
├── docker-compose.yml
└── .env.example
```

## Compliance & Security

- **NDPA**: Nigeria Data Protection Act compliance — all PII in af-south-1
- **PCI-DSS Level 2**: No card data on ISEYAA servers; tokenised via Paystack Vault
- **CBN Guidelines**: All financial flows CBN-compliant
- **RBAC**: Role-based access at API Gateway + service level
- **Encryption**: TLS 1.3 in transit; KMS at rest

## Contributing

All development follows PRD v2.0. Any stack deviations require written CTO approval.  
See [SPRINT-1-PLAN.md](docs/sprint/SPRINT-1-PLAN.md) for current sprint tasks.

---

*Ogun State Government Digital Transformation Programme | Confidential*
