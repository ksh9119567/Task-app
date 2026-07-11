# Changelog

All notable changes will be documented in this file.

---

## [v0.4.0] - 2026-07-11
### Added
- Governance app: per-entity settings (Organization / Team / Project) auto-created via signals
- Configurable min/max role policies, membership rules, creation controls, limits & default roles
- Rules-resolution engine with settings inheritance (Project ← Team ← Org)
- Activity tracking middleware: automatic audit log of all API requests
- Activity Logs API: list, detail, `my_activities`, and `stats`
- Sensitive-field redaction in logs + activity-log cleanup management command
- Tasks: `get-my-tasks/` cross-project view endpoint

### Changed
- Corrected task/priority choice formats and role choice formats

### Notes
- Approval **workflow** engine is not yet implemented — governance exposes
  `require_approval_for_*` flags, but there is no request/approve/reject queue yet.
- `sprints` and `comments` apps are scaffolded but not yet implemented.

---

## [v0.3.0] - 2026
### Added
- CRUD Projects: org/team-linked or standalone, lifecycle status
  (Planning / Active / On Hold / Completed / Archived)
- Project membership: invite, accept, update role, remove, self-remove, transfer ownership
- CRUD Tasks: status, priority, type, dates, assignee
- Subtask support (self-referential, one level deep)
- Task filtering, search, ordering & pagination

---

## [v0.2.0] - 2026
### Added
- Full Teams module: CRUD, membership invite, roles, ownership transfer
- OTP verification & OTP login
- Forgot-password flow (request → verify → reset)
- Asynchronous email delivery via Celery (OTP & invites)

---

## [v0.1.0] - 2025-11-24
### Added
- Custom User model (email-based)
- JWT authentication (access/refresh in Redis)
- Docker setup (Postgres + Redis + Celery)
- Git workflow and branching rules
- RBAC Skeleton & Permission Classes
- CRUD Organizations, membership invite, roles
- CRUD Teams, membership invite, roles

---

## Upcoming
### Planned
- Approval workflow engine (activate governance approval flags)
- Comments module (task & project discussions, attachments)
- Sprints module (planning, backlog, burndown)
- Notifications (assignments, mentions, invites, due dates)
