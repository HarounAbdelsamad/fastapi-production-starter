# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Enterprise hardening roadmap execution phase 2 baseline:
  - Rate limiting and request ID middleware
  - Error envelope standardization
  - API versioning under `/api/v1`
  - Security headers, deep health probes, metrics and sentry toggles
  - API key auth, login throttling, audit logs
  - Soft delete mixin, file uploads, CLI, feature flags, ws and oauth scaffolding

## [0.1.0] - 2026-04-10

### Added
- FastAPI starter with async SQLAlchemy, auth, RBAC, pagination.
- Redis, Celery, Docker compose stack, CI lint/test workflow.
- Initial Alembic migrations and deployment documentation.
