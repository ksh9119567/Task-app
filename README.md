# 🚀 Structra Backend

> A Governance-Aware Work Management Engine\
> Designed for Structured Collaboration & Enterprise-Grade Control

Structra is a scalable backend platform engineered to power structured
work execution across Organizations, Teams, and Projects.

This repository contains the **Structra Backend Service** --- a
multi-tenant, RBAC-driven system built with Django and Django REST
Framework. It is designed not just as a task manager, but as a
governance-first collaboration engine capable of scaling into enterprise
environments.

------------------------------------------------------------------------

# 🌍 Vision

Structra aims to become a **governed work orchestration platform** where
organizations can:

-   Manage structured hierarchies (Org → Team → Project)
-   Enforce configurable role-based policies
-   Execute controlled workflows with approvals
-   Track productivity through sprints & analytics
-   Maintain audit integrity with soft-delete architecture
-   Scale towards enterprise-grade infrastructure

The system is intentionally designed for:

-   Multi-tenant scalability
-   Clear governance boundaries
-   Future microservice extraction
-   Production readiness

------------------------------------------------------------------------

# 🏗 Architecture Overview

Structra follows a **Governance-Oriented Modular Monolith** design.

    Organization → Team → Project → Task → Subtask

### Boundary Model

-   **Organization** → Governance & billing boundary\
-   **Team** → Structural grouping\
-   **Project** → Security & execution boundary\
-   **Task** → Work execution unit

### Internal Structure

    app/
    ├── accounts/        # Authentication & user lifecycle
    ├── organizations/   # Organization governance & policies
    ├── teams/           # Team management
    ├── projects/        # Project boundaries & RBAC rules
    ├── tasks/           # Task & subtask execution
    ├── governance/      # Configurable settings & policy resolution engine
    ├── sprints/         # Sprint planning (scaffolded — not yet implemented)
    └── comments/        # Comments & discussion layer (scaffolded — not yet implemented)

    core/                # Role hierarchy, policy engine, permissions, activity logging
    services/            # Business logic layer (token store, etc.)
    config/              # Django settings
    docs/                # Documentation
    scripts/             # Utility scripts

### Key Design Principles

-   Clear separation of governance vs execution
-   Explicit access boundaries
-   Centralized policy engine (min/max role control)
-   Role hierarchy enforcement
-   Soft-delete lifecycle management
-   Future microservice extraction capability

------------------------------------------------------------------------

# ⚙️ Tech Stack

  Layer              Technology
  ------------------ -----------------------------------
  Language           Python 3.12
  Framework          Django 5.2
  API Layer          Django REST Framework
  Database           PostgreSQL 15
  Cache              Redis 7
  Async Tasks        Celery 5.5.3
  Containerization   Docker & Docker Compose
  Authentication     JWT (Access + Refresh Tokens)
  Logging            Structured logging & audit trails

------------------------------------------------------------------------

# 🔐 Authentication & Security

-   Custom email-based user model
-   JWT authentication (access + refresh)
-   Refresh token storage via Redis
-   OTP & password reset support
-   Token blacklisting
-   Role-Based Access Control (Org / Team / Project)
-   Configurable policy engine
-   Soft-delete lifecycle protection

------------------------------------------------------------------------

# 🚀 Current Features

> ✅ = implemented & available · 🔜 = scaffolded / planned (see Roadmap)

### Accounts & Identity ✅

-   Custom email-based user model with soft delete
-   JWT authentication (access + refresh) with Redis-backed token store & revocation
-   OTP generation/verification (email) and OTP login
-   Forgot-password flow (request → verify → reset)
-   Profile management (name, username, phone, profile picture)
-   Asynchronous email delivery via Celery (OTP & invites, with retries)

### Governance Layer ✅

-   Single-owner model per entity with transferable ownership
-   Admin / Manager delegation
-   Configurable role thresholds (min/max policy model) per org / team / project
-   Auto-created settings objects with sensible defaults (via signals)
-   Rules engine resolving effective policies, including inheritance (project ← team ← org)
-   🔜 Approval **workflow** engine (settings flags exist today; request/approve/reject queue not yet built)

### Organization & Team Management ✅

-   Structured hierarchy management (Org → Team → Project)
-   Full CRUD + membership: invite (email token), accept, update role, remove, self-remove, transfer ownership
-   Team-to-project mapping
-   Governance protection against orphaned entities

### Project & Task System ✅

-   Project lifecycle status (Planning / Active / On Hold / Completed / Archived)
-   Full task CRUD with status, priority, type, dates & assignee
-   Self-referential subtask architecture (one level)
-   "My Tasks" cross-project view
-   Filtering, search, sorting & pagination
-   Configurable create/update/delete policies (governed by Project settings)

### Activity & Audit ✅

-   Automatic activity tracking of all API requests via middleware
-   Audit log with who/what/when/where, action stats & my-activity feed
-   Sensitive-field redaction and automatic log cleanup command

### Productivity & Planning 🔜

-   Sprint module (scaffolded — not yet implemented)
-   Timeline / burndown / workload analytics (planned)

### Infrastructure ✅

-   Dockerized environment (Postgres + Redis + Celery)
-   Redis integration & Celery background jobs
-   Centralized permission engine
-   Soft-delete lifecycle across users, orgs, teams, projects, tasks

------------------------------------------------------------------------

# 📈 Roadmap

## Phase 1 --- Governance & Policy Engine (Completed)

-   Configurable min/max role policies
-   Self-removal safeguards
-   Ownership transfer flow
-   Settings inheritance & rules-resolution engine

## Phase 2 --- Core Work Management (Completed)

-   Projects CRUD, membership & lifecycle status
-   Tasks CRUD, subtasks, assignment, filtering & "My Tasks"
-   Automatic activity tracking & audit logs

## Phase 3 --- Approval & Collaboration Layer (In Progress)

-   Approval **workflow** engine (turn governance flags into request/approve/reject queues)
-   Comment system (task & project discussions)
-   Notifications (assignments, mentions, invites, due dates)
-   Project / team chat & org announcements

## Phase 4 --- Sprint & Productivity

-   Sprint lifecycle management
-   Velocity tracking
-   Burndown reports
-   Workload analytics

## Phase 5 --- Subscription & Scale

-   Plan-based feature flags
-   Usage-based limits
-   Stripe integration
-   Rate limiting

## Phase 6 --- Infrastructure Hardening

-   Redis caching layers
-   Audit logs (enterprise)
-   Object storage (S3)
-   Observability & monitoring

------------------------------------------------------------------------

# 🐳 Running Locally (Docker)

``` bash
docker compose build
docker compose up -d
```

Access API at: 👉 http://localhost:8000

------------------------------------------------------------------------

# 📦 API Structure

All APIs are versioned and modular:

    /api/v1/accounts/
    /api/v1/organizations/
    /api/v1/teams/
    /api/v1/projects/
    /api/v1/tasks/
    /api/v1/governance/
    /api/v1/activity-logs/

See [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) for the full endpoint catalog.
Future API versions can coexist without breaking backward compatibility.

------------------------------------------------------------------------

# 🧠 Engineering Goals

Structra Backend is built to demonstrate:

-   Enterprise-grade RBAC architecture
-   Policy-driven governance systems
-   Clean modular monolith design
-   Multi-tenant database modeling
-   Soft-delete lifecycle integrity
-   Scalable backend system design

------------------------------------------------------------------------

# 🤝 Contributing

1.  Fork the repository\
2.  Create a feature branch from `develop`\
3.  Follow conventional commits\
4.  Submit a Pull Request

### Branch Strategy

-   `main` → Stable releases\
-   `develop` → Active development

------------------------------------------------------------------------

# 📜 License

MIT License (To be added officially)

------------------------------------------------------------------------

# 👨‍💻 Author

Developed by **Kunal Sharma**\
Backend Engineer \| System Design Enthusiast

------------------------------------------------------------------------

# ⭐ Support

If you find Structra valuable, consider starring the repository ⭐

------------------------------------------------------------------------

**Status:** Active Development\
**Last Updated:** July 2026
