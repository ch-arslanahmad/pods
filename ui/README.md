# Pods UI

Standalone React dashboard for pods. It is built against a single contract and
runs entirely on **seed data** — no Python server, no SQLite, no network.

This is the seed-first UI from issue
[#2](https://github.com/ch-arslanahmad/pods/issues/2). Wiring it to the real
server is a separate PR.

## Quick start

```bash
cd ui
npm install
npm run dev
```

Open the printed URL. Seed mode is the default, so the full app works with zero
backend.

## Scripts

| Script            | Does                                 |
| ----------------- | ------------------------------------ |
| `npm run dev`     | Vite dev server with HMR             |
| `npm run build`   | Typecheck (`tsc -b`) + production build |
| `npm run preview` | Serve the production build locally   |
| `npm run lint`    | oxlint, including the contract boundary |

## Architecture

```
src/
├── api/
│   ├── types.ts       Pod, ListPodsParams, PodsContract — the single contract
│   ├── seed.ts        ~30 realistic pods (categories, projects, JSON content, soft deletes)
│   ├── seedClient.ts  PodsContract over the seed dataset, with artificial latency
│   ├── http.ts        PodsContract over the real REST API (stub)
│   └── client.ts      the one switch: seed vs http
├── components/        Background, Header, Sidebar, Pagination, loading/error/empty states
├── features/pods/     PodList, PodDetail, PodForm
├── hooks/             useDebounce
├── lib/format.ts      timestamp, preview, and JSON helpers
├── App.tsx            filters + list ↔ detail ↔ create/edit routing (state, no router)
└── main.tsx           React Query provider
```

**The rule:** screens import `api` from `api/client.ts` and types from
`api/types.ts`. They never import `seed.ts`, `seedClient.ts`, `http.ts`, or call
`fetch` directly. `npm run lint` enforces this.

## The contract

`src/api/types.ts` is the source of truth. It mirrors `db/schema.sql` and
`api.py`:

| Method                          | Purpose                                    |
| ------------------------------- | ------------------------------------------ |
| `ping()`                        | health check for the header indicator      |
| `listPods(params)`              | search + filters + pagination → `{ pods, total }` |
| `getPod(id)`                    | one pod                                    |
| `createPod(input)`              | create                                     |
| `updatePod(id, patch)`          | partial update                             |
| `deletePod(id)`                 | soft delete                                |
| `listCategories()`              | distinct categories                        |
| `listProjects()`                | distinct projects                          |

`ListPodsParams` is `query`, `category`, `project`, `created_after`,
`created_before`, `limit`, `offset`.

## Switching seed → HTTP

Set one environment variable:

```bash
cp .env.example .env
# edit .env → VITE_API_MODE=http
```

No screen changes are needed. `http.ts` currently throws `not implemented`; the
integration PR fills it in.

## Notes for the integration PR

`http.ts` must bridge three differences between the contract and the current
backend:

1. **Envelope.** Every response is wrapped: `{ success: true, data: ... }`.
2. **No `total`.** `GET /api/pods` returns an array only. Add a `COUNT(*)` to
   `find_pods` (or a dedicated endpoint) so pagination can report "X of Y".
3. **Timestamps.** SQLite returns `"YYYY-MM-DD HH:MM:SS"`, not ISO-8601. The
   UI normalises both formats in `lib/format.ts`, but `http.ts` should return
   ISO for consistency.

## Seed behaviour

The seed client deliberately mimics the backend:

- `total` counts matches **before** `limit`/`offset`
- soft-deleted pods (`deleted_at !== null`) are hidden from list and get
- search matches name, content, category, and project
- every call has 220–340 ms of simulated latency so loading states are real
- timestamps are relative to load time, so Today / This week / This month always
  have results
