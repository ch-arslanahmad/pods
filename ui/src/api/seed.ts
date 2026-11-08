import type { Pod } from './types'

// Seed data mirrors db/schema.sql. Timestamps are relative to load time so the
// Today / This week / This month filters always have something to show.
const DAY_MS = 86_400_000
const NOW = Date.now()

function iso(daysAgo: number, hour = 9, minute = 0): string {
  const date = new Date(NOW - daysAgo * DAY_MS)
  date.setHours(hour, minute, 0, 0)
  return date.toISOString()
}

type SeedSpec = {
  pod_name: string
  category: string
  content: string
  project: string | null
  created_days_ago: number
  updated_days_ago?: number
  deleted_days_ago?: number
  hour?: number
  minute?: number
}

const specs: SeedSpec[] = [
  {
    pod_name: 'Pods contract decisions',
    category: 'decision',
    project: 'pods',
    created_days_ago: 0,
    hour: 9,
    minute: 12,
    content: JSON.stringify({
      decisions: [
        'content is one JSON string bag, not two columns',
        'project is a plain text label, not a foreign key (for now)',
        'soft deletes only — deleted_at, never hard delete',
      ],
      next: 'Wire the HTTP client in the integration PR',
    }),
  },
  {
    pod_name: 'Meeting: UI scope for issue #2',
    category: 'meeting',
    project: 'pods',
    created_days_ago: 0,
    hour: 11,
    minute: 40,
    content:
      'Agreed to ship the dashboard against seed data first. No backend changes in this PR. The contract is the boundary: screens never touch fetch or seed directly.',
  },
  {
    pod_name: 'Dyno matching algorithm idea',
    category: 'idea',
    project: 'dyno-matching-app',
    created_days_ago: 0,
    hour: 15,
    minute: 5,
    content:
      'Score compatibility from shared interests plus complementary traits. Start with a weighted Jaccard similarity, then layer in recency of activity. Keep the weights in one config object so they are easy to tune.',
  },
  {
    pod_name: 'FTS5 search notes',
    category: 'learning',
    project: 'pods',
    created_days_ago: 1,
    hour: 10,
    minute: 20,
    content:
      'External-content FTS5 tables stay in sync through triggers. A second AFTER UPDATE trigger with a nested UPDATE corrupts the index — that is why migration 004 dropped set_pods_timestamp and updated_at is now set in SQL.',
  },
  {
    pod_name: 'Workbase RBAC model',
    category: 'reference',
    project: 'workbase',
    created_days_ago: 2,
    hour: 14,
    minute: 0,
    content: JSON.stringify({
      roles: ['owner', 'admin', 'member', 'viewer'],
      rules: {
        owner: 'everything, including billing',
        admin: 'manage members and workspaces',
        member: 'read and write workspace content',
        viewer: 'read only',
      },
    }),
  },
  {
    pod_name: 'Career counselor roadmap data',
    category: 'learning',
    project: 'career-counselor-ai',
    created_days_ago: 3,
    hour: 16,
    minute: 30,
    content:
      'Each degree program needs semester-wise courses plus a short roadmap. Store the roadmap as ordered steps with a title and one-line rationale so the UI can render it as a timeline.',
  },
  {
    pod_name: 'SQLite connection caching',
    category: 'learning',
    project: 'pods',
    created_days_ago: 5,
    hour: 8,
    minute: 45,
    content:
      'Cache one connection per DB_PATH instead of opening and closing on every call. Write operations roll back on error so the shared connection never holds a stale transaction.',
  },
  {
    pod_name: 'Portfolio hero copy',
    category: 'general',
    project: 'personal-portfolio',
    created_days_ago: 6,
    hour: 19,
    minute: 10,
    content:
      'Headline: "I build tools that make hard things feel simple." Subhead should name three concrete outcomes, not adjectives. Keep it under 30 words.',
  },
  {
    pod_name: 'Soft delete strategy',
    category: 'decision',
    project: 'pods',
    created_days_ago: 8,
    hour: 13,
    minute: 15,
    content: JSON.stringify({
      column: 'deleted_at',
      behaviour: 'hidden from list and get, retained in the table',
      rationale: 'recoverable data and a future restore view',
    }),
  },
  {
    pod_name: 'React Query invalidation cheatsheet',
    category: 'snippet',
    project: null,
    created_days_ago: 9,
    hour: 9,
    minute: 30,
    content:
      "After a mutation, invalidate every query key the mutation can change:\n\nqueryClient.invalidateQueries({ queryKey: ['pods'] })\nqueryClient.invalidateQueries({ queryKey: ['pod', id] })\nqueryClient.invalidateQueries({ queryKey: ['categories'] })\nqueryClient.invalidateQueries({ queryKey: ['projects'] })",
  },
  {
    pod_name: 'Bug: FTS corruption on update',
    category: 'bug',
    project: 'pods',
    created_days_ago: 12,
    hour: 17,
    minute: 55,
    content:
      'Symptom: "database disk image is malformed" after updating a pod. Cause: nested UPDATE inside an AFTER UPDATE trigger on an external-content FTS5 table. Fix: drop the timestamp trigger, set updated_at in application SQL, rebuild the index.',
  },
  {
    pod_name: 'Vite + React setup steps',
    category: 'snippet',
    project: null,
    created_days_ago: 14,
    hour: 11,
    minute: 0,
    content:
      'npm create vite@latest ui -- --template react-ts\ncd ui && npm install\nnpm install @tanstack/react-query\nnpm run dev',
  },
  {
    pod_name: 'Semester course schema',
    category: 'reference',
    project: 'career-counselor-ai',
    created_days_ago: 16,
    hour: 10,
    minute: 10,
    content: JSON.stringify({
      program: 'BSc Computer Science',
      semesters: [
        { term: 1, courses: ['Programming I', 'Discrete Math'] },
        { term: 2, courses: ['Data Structures', 'Linear Algebra'] },
      ],
    }),
  },
  {
    pod_name: 'Design tokens',
    category: 'reference',
    project: 'personal-portfolio',
    created_days_ago: 18,
    hour: 20,
    minute: 25,
    content: JSON.stringify({
      spacing: [4, 8, 12, 16, 24, 32, 48],
      radius: { card: 12, pill: 999 },
      type: { body: 16, small: 14, h1: 40 },
    }),
  },
  {
    pod_name: 'Python typing notes',
    category: 'learning',
    project: null,
    created_days_ago: 20,
    hour: 7,
    minute: 50,
    content:
      'Prefer built-in generics (list[str], dict[str, int]) over typing.List. Use `str | None` over Optional[str]. Keep type hints on public functions; skip them on short local helpers.',
  },
  {
    pod_name: 'Dyno onboarding flow',
    category: 'idea',
    project: 'dyno-matching-app',
    created_days_ago: 22,
    hour: 12,
    minute: 35,
    content:
      'Three screens: interests, deal-breakers, photo. Ask for the minimum needed to compute a first match, then let people refine later. Never block the first match on a long profile.',
  },
  {
    pod_name: 'Workbase auth checklist',
    category: 'reference',
    project: 'workbase',
    created_days_ago: 25,
    hour: 9,
    minute: 5,
    content:
      'Session cookies httpOnly + secure, CSRF token on state-changing requests, rate limit login, rotate session on privilege change, log failed attempts without storing passwords.',
  },
  {
    pod_name: 'Deployment tunnel notes',
    category: 'reference',
    project: 'pods',
    created_days_ago: 28,
    hour: 18,
    minute: 40,
    content:
      'ngrok exposes the local Starlette app for MCP HTTP mode. Keep the tunnel command separate from the server process so either can restart without the other. Print the public URL on start.',
  },
  {
    pod_name: 'Tailwind vs CSS modules',
    category: 'decision',
    project: null,
    created_days_ago: 31,
    hour: 15,
    minute: 20,
    content:
      'For this dashboard, plain CSS with variables wins: one stylesheet, no build plugin, theme switching through prefers-color-scheme. Revisit if the component count grows past a few dozen.',
  },
  {
    pod_name: 'Pod list pagination rules',
    category: 'decision',
    project: 'pods',
    created_days_ago: 34,
    hour: 10,
    minute: 0,
    content:
      'total counts every row that matches the filters, before limit and offset. Reset offset to zero whenever a filter changes so pages never start past the end of the result set.',
  },
  {
    pod_name: 'Search ranking with BM25',
    category: 'idea',
    project: 'pods',
    created_days_ago: 38,
    hour: 13,
    minute: 45,
    content:
      'FTS5 already computes BM25 but we throw it away. Select bm25(pods_fts) as rank and order by it when a query is present. Fall back to created_at DESC when there is no query.',
  },
  {
    pod_name: 'Portfolio project brief',
    category: 'general',
    project: 'personal-portfolio',
    created_days_ago: 42,
    hour: 16,
    minute: 10,
    content:
      'Three sections: selected work, a short about, contact. Each project card needs one outcome sentence and a live link. No carousel — a simple grid is faster and easier to scan.',
  },
  {
    pod_name: 'MCP tool naming',
    category: 'reference',
    project: 'pods',
    created_days_ago: 47,
    hour: 8,
    minute: 30,
    content:
      'Tools follow pods_verb: pods_add, pods_find, pods_get, pods_update, pods_delete, pods_ping. Keep the prefix so agents can group them, and keep names short enough to type in a prompt.',
  },
  {
    pod_name: 'Career counselor prompts',
    category: 'snippet',
    project: 'career-counselor-ai',
    created_days_ago: 52,
    hour: 11,
    minute: 55,
    content: JSON.stringify({
      system: 'You are a career counselor. Recommend degree programs from stated interests.',
      constraints: ['cite the interest that drove each pick', 'never invent programs'],
    }),
  },
  {
    pod_name: 'Dyno match scoring v1',
    category: 'decision',
    project: 'dyno-matching-app',
    created_days_ago: 58,
    hour: 14,
    minute: 20,
    content:
      'v1 score = 0.6 * shared interests + 0.3 * complementary traits + 0.1 * activity recency. Ship it, log the inputs, and tune the weights once there is real feedback.',
  },
  {
    pod_name: 'Workbase workspace isolation',
    category: 'learning',
    project: 'workbase',
    created_days_ago: 63,
    hour: 9,
    minute: 40,
    content:
      'Every query must be scoped by workspace_id. Enforce it in the repository layer, not the route handlers, so a forgotten filter cannot leak rows across organisations.',
  },
  {
    pod_name: 'SQLite backup/restore',
    category: 'learning',
    project: 'pods',
    created_days_ago: 70,
    hour: 17,
    minute: 15,
    content:
      'Use the backup API or VACUUM INTO for a consistent copy while the app is running. Restore needs a pre-flight check so a bad file never overwrites a healthy database.',
  },
  {
    pod_name: 'CSS grid notes',
    category: 'snippet',
    project: null,
    created_days_ago: 76,
    hour: 20,
    minute: 5,
    content:
      '.grid {\n  display: grid;\n  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));\n  gap: 1rem;\n}',
  },
  {
    pod_name: 'Project cartel downloader idea',
    category: 'idea',
    project: null,
    created_days_ago: 84,
    hour: 12,
    minute: 0,
    content:
      'A general downloader that queues links, detects media type, and resumes interrupted transfers. Start with direct HTTP, add yt-dlp as an optional backend later.',
  },
  {
    pod_name: 'Epstien chat app plan',
    category: 'idea',
    project: null,
    created_days_ago: 91,
    hour: 15,
    minute: 45,
    content:
      'Chat app with rooms, presence, and message history. Use websockets for delivery and store messages append-only. Keep the first version text-only.',
  },
  {
    pod_name: 'JS event loop notes',
    category: 'learning',
    project: null,
    created_days_ago: 99,
    hour: 10,
    minute: 25,
    content:
      'Synchronous code runs first, then microtasks (promises), then macrotasks (timers, I/O). An await yields to the microtask queue, which is why a tight promise chain can starve rendering.',
  },
  {
    pod_name: 'Old draft: pods v0 spec',
    category: 'general',
    project: 'pods',
    created_days_ago: 112,
    updated_days_ago: 105,
    deleted_days_ago: 100,
    content:
      'Superseded by the current schema. Kept only to exercise the soft-delete path in the seed dataset.',
  },
  {
    pod_name: 'Scratch: random links',
    category: 'general',
    project: null,
    created_days_ago: 6,
    updated_days_ago: 4,
    deleted_days_ago: 2,
    hour: 21,
    minute: 30,
    content: 'A temporary list that was cleared after the links were filed properly.',
  },
  {
    pod_name: 'Duplicate: portfolio brief',
    category: 'general',
    project: 'personal-portfolio',
    created_days_ago: 41,
    updated_days_ago: 30,
    deleted_days_ago: 20,
    hour: 16,
    minute: 12,
    content: 'An accidental duplicate of the portfolio brief, soft-deleted after the merge.',
  },
]

export const seedPods: Pod[] = specs.map((spec, index) => ({
  id: index + 1,
  pod_name: spec.pod_name,
  category: spec.category,
  content: spec.content,
  project: spec.project,
  created_at: iso(spec.created_days_ago, spec.hour, spec.minute),
  updated_at: iso(
    spec.updated_days_ago ?? spec.created_days_ago,
    spec.hour,
    spec.minute,
  ),
  deleted_at:
    spec.deleted_days_ago === undefined ? null : iso(spec.deleted_days_ago),
}))
