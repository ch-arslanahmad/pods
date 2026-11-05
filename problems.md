# Current Problems - pods

> Living doc. Created 2026-08-08. Tracked as a pointer pod (see "Pod tracking" at bottom).
> Update this file; the pod only links here.

## Bug 1 - FTS search doesn't cover `category` / `project` — Fixed

**Symptom:** `pods_find(query="workspace")` returns empty even though `workspace` is a category. FTS5 index only covers `pod_name` + `content` (`db/schema.sql:23-27`); `category` is a separate column.

**Fix:** `pods_find()` broadens the query to `WHERE (pods_fts MATCH ? OR p.category LIKE ? OR p.project LIKE ?)`. Handled by migration `002_fix_timestamps_and_indexes.py`.

## Bug 2 - Timestamp format mismatch — Fixed

**Symptom:** `created_at` = `08-08-2026,04:59:44` (DD-MM-YYYY) but `updated_at` = `2026-08-08 10:00:03` (YYYY-MM-DD) on the same row.

**Root cause:** schema was **duplicated and diverged** (now cleaned up):
- `db/database.py` previously embedded its own CREATE TABLE with `strftime('%d-%m-%Y,%H:%M:%S')` defaults (old format)
- migration `001_initial_schema.py` executes `db/schema.sql` which uses `datetime('now','localtime')` (new format)

Live DB was created under the **old** default; `CREATE TABLE IF NOT EXISTS` never fixes existing tables, and the update **trigger** always writes `datetime()`, so the divergence persists forever. `database.py` has since been cleaned up (no more embedded DDL), but the live DB still has mixed timestamps until migration 002 is applied.

**Side effect:** `ORDER BY created_at DESC` sorts wrong because DD-MM-YYYY and YYYY-MM-DD interleave lexically.

**Fix:** Migration `002_fix_timestamps_and_indexes.py` rebuilt the table (new-table -> copy -> drop -> rename) so both columns use `datetime('now','localtime')` and converted existing rows. Dead duplicate DDL was removed from `database.py`; `schema.sql` is the single source of truth.

## Bug 3 - Soft-delete corrupts FTS5 index (`database disk image is malformed`) — Fixed

**Symptom:** create -> soft-delete -> create -> soft-delete throws
`sqlite3.DatabaseError: database disk image is malformed` from the FTS5 trigger.
Made `pods_delete` (and any UPDATE on `pods`) unusable; hit on the live DB too.

**Root cause:** upstream SQLite bug — an external-content FTS5 sync trigger
(`pods_fts_update`) gets corrupted by a second AFTER UPDATE trigger that issues a
nested UPDATE on the same table (`set_pods_timestamp` bumping `updated_at`).
Either trigger alone is fine; together they desync the FTS shadow tables.
Reference: sqlite.org/bugs — "External-content FTS5 index corrupted by a second
AFTER UPDATE trigger issuing a nested UPDATE on the content tab".
Not caused by connection caching (reproduced with per-call connections).

**Fix:** migration `004_drop_set_pods_timestamp.py` drops the `set_pods_timestamp`
trigger and rebuilds the index. `updated_at` is now set by SQL in
`update_pod()` / `delete_pod()` instead of a trigger. `schema.sql` updated to match.

## Open problem - Unwanted AI data pollution

An AI agent with access to `pods_add` can insert data into the knowledge base without the user's explicit intent or awareness. An LLM may misinterpret context, fabricate information, or save trivial/incorrect data during a conversation. Over time this dilutes signal-to-noise: search gets less useful, curated categories get polluted, trust in retrieved data drops.

Compounded by scale, a single chat session can produce dozens of unintended writes before the user notices. Since the user didn't create the data, they may not recognize it as junk later.

**Not yet solved**, thinking through approaches. (moved here from features.md / PLAN.md)

## Open problem - Token-inefficient retrieval in `pods_find` — Priority: High

Every `pods_find` call returns up to 50 full pod rows, full `content` included, newest-first. That is the default, so a caller that just wants to "see what's there" pulls ~50 rows of prose into the model context.

**Why fix (token cost is the reason):** tokens are the scarce resource for an agent memory server. Bloated results crowd out the conversation, cost money on every call, and raise the odds the model skips the pod that actually mattered.

- **Default `limit` is 50** (`server.py:64`, `api.py:22`). At the measured ~686 chars/pod average (see Storage math below), that is ~34KB / ~8-9K tokens per call before any filtering. A default of 10-15 keeps the same usefulness at roughly a quarter of the tokens.
- **No `has_more` / total signal.** The caller cannot tell whether it saw everything, so it either guesses and re-queries (doubling tokens) or over-fetches `limit` to be safe (paying for rows it discards).
- **No field projection.** `content` is always returned even when the caller only needs `pod_name` / `category` / `id` to decide what to fetch next. A `fields` / `snippet` option would let the agent do a cheap first pass.

These compound: the current shape makes the *cheap* path (browse) as expensive as the *expensive* path (read everything), which is backwards for a memory tool.

**Priority: High — token efficiency is a core requirement, not a nice-to-have.** Every retrieval path in an agent loop pays this cost repeatedly, so a smaller default plus a has-more signal have outsized leverage. Fix before adding features that return more data.


## Open Probelm: 

Able to search pods using CLI by user or local agent to get results, get output in `json` or any human-agent readable format (substring-search for now) .

## Scalability notes

### Single user (today: 68 pods, ~160KB DB) - healthy
- SQLite + FTS5 fine to millions of rows at current write rates
- stdio transport = 1 client; WAL handles read concurrency
- Backup = copy the file

### Storage math (measured 2026-08-08)

- 40 live pods, avg ~686 chars, max ~1,876 chars → 140KB DB (≈3.5KB/pod incl. FTS index + page overhead)
- Linear scaling: 10MB ≈ 2,900 avg pods / ~850 big pods; 100MB ≈ 29,000 / ~8,500
- **Storage is the last limit we'll hit** — SQLite + FTS5 handles millions of rows fine. Real problems at 1,000+ pods are search quality (BM25 ranking), dedup accumulation, and context flooding from unranked `pods_find` results — not capacity.

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

- Pod: `Pods repo - problems doc` (category `problems`, project `pods`)
- This file (`problems.md`) is canonical; the pod is a pointer here, not a copy — no sync burden. Update this file only.
