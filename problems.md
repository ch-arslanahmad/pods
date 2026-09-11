# Current Problems - pods

> Living doc. Created 2026-08-08. Tracked as a pod (see "Pod tracking" at bottom).
> Update this file + the pod together whenever status changes.

## Bug 1 - FTS search doesn't cover `category` / `project` — Fixed

**Symptom:** `pods_find(query="workspace")` returns empty even though `workspace` is a category. FTS5 index only covers `pod_name` + `content` (`db/schema.sql:23-27`); `category` is a separate column.

**Fix:** `pods_find()` broadens the query to `WHERE (pods_fts MATCH ? OR p.category LIKE ? OR p.project LIKE ?)`. Handled by migration `002_fix_timestamps_and_indexes.py`.

## Bug 2 - Timestamp format mismatch

**Symptom:** `created_at` = `08-08-2026,04:59:44` (DD-MM-YYYY) but `updated_at` = `2026-08-08 10:00:03` (YYYY-MM-DD) on the same row.

**Root cause:** schema was **duplicated and diverged** (now cleaned up):
- `db/database.py` previously embedded its own CREATE TABLE with `strftime('%d-%m-%Y,%H:%M:%S')` defaults (old format)
- migration `001_initial_schema.py` executes `db/schema.sql` which uses `datetime('now','localtime')` (new format)

Live DB was created under the **old** default; `CREATE TABLE IF NOT EXISTS` never fixes existing tables, and the update **trigger** always writes `datetime()`, so the divergence persists forever. `database.py` has since been cleaned up (no more embedded DDL), but the live DB still has mixed timestamps until migration 002 is applied.

**Side effect:** `ORDER BY created_at DESC` sorts wrong because DD-MM-YYYY and YYYY-MM-DD interleave lexically.

**Fix:** Migration `002_fix_timestamps_and_indexes.py` rebuilt the table (new-table -> copy -> drop -> rename) so both columns use `datetime('now','localtime')` and converted existing rows. Dead duplicate DDL was removed from `database.py`; `schema.sql` is the single source of truth.

## Open problem - Unwanted AI data pollution

An AI agent with access to `pods_add` can insert data into the knowledge base without the user's explicit intent or awareness. An LLM may misinterpret context, fabricate information, or save trivial/incorrect data during a conversation. Over time this dilutes signal-to-noise: search gets less useful, curated categories get polluted, trust in retrieved data drops.

Compounded by scale, a single chat session can produce dozens of unintended writes before the user notices. Since the user didn't create the data, they may not recognize it as junk later.

**Not yet solved**, thinking through approaches. (moved here from features.md / PLAN.md)

## Scalability notes

### Single user (today: 68 pods, ~160KB DB) - healthy
- SQLite + FTS5 fine to millions of rows at current write rates
- stdio transport = 1 client; WAL handles read concurrency
- Backup = copy the file

### Multi-user - blocker order (most to least urgent)
1. **No identity:** pods have no `user_id`/owner column. Every query needs `WHERE user_id = ?`, FTS needs user filter, `category`/`project` labels collide across users.
2. **No auth on HTTP API:** server binds `0.0.0.0:8000` behind cloudflared/ngrok (`tunnel.py`), anyone reaching that URL can read/write all pods. Fix before publishing the tunnel.
3. **SQLite single-writer lock:** WAL = 1 writer + N readers; 2+ concurrent writers -> `database is locked`. Ceiling = a handful of concurrent writers -> then Postgres or Turso.
4. **Semantics:** dedup (`UNIQUE(pod_name, content, project)`) must become user-scoped; sessions/provenance (AGENTS.md gaps #1/#2) needed to stop cross-user search leakage.
5. **Ops:** backups, live migrations, rate limiting, pagination.

### Verdict
- Self + a few friends: stay SQLite, add `user_id` scoping + token auth. No perf wall before ~100 users' worth of pods.
- Only move to Postgres/Turso when expecting dozens of **concurrent writer agents** or public internet exposure. Not preemptively.

## Pod tracking

- Pod: `Pods repo - problems doc` (category `problems`, project `pods`), created 2026-08-08
- This file: `problems.md` at repo root
- Keep both in sync when a bug gets fixed.
