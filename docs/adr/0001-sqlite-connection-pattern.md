# ADR 0001: SQLite Connection Pattern

**Status:** Accepted
**Date:** 2026-07-19

## Context

Server supports stdio (sequential) and HTTP (concurrent) modes. SQLite allows one writer at a time. WAL helps reads, not writes. Question: module-level singleton or connection-per-call?

## Decision

Keep connection-per-call. Each function opens and closes its own connection.

## Why

- HTTP mode is concurrent — multiple sessions can hit the server
- Shared connection risks thread-safety violations, transaction leaks, SQLITE_BUSY errors
- Connection-per-call is isolated and safe
- SQLite open/close is cheap (microseconds)
- Singleton would break HTTP mode

## Consequences

- Each tool call pays `sqlite3.connect()` cost, negligible for SQLite
- Safe for both stdio and HTTP modes
- DB is migrated to Turso, code not yet switched — revisit connection pooling when updating code to use Turso
