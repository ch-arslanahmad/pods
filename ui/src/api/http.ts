import type { PodsContract } from './types'

// The real transport. Intentionally a stub: this issue ships the seed-backed UI
// only. The follow-up integration PR fills these in against api.py.
//
// Agents are UI-only mocks for now — the backend has no agent endpoints yet.
//
// Three known mismatches to handle then:
//   1. Responses are wrapped in { success: true, data: ... }.
//   2. GET /api/pods returns an array with no `total` (needs a COUNT query).
//   3. Timestamps come back as "YYYY-MM-DD HH:MM:SS", not ISO-8601.
async function notImplemented(method: string): Promise<never> {
  throw new Error(
    `${method} is not implemented yet — set VITE_API_MODE=seed or wire the HTTP client`,
  )
}

export const httpClient: PodsContract = {
  ping: () => notImplemented('ping'),
  listPods: () => notImplemented('listPods'),
  getPod: () => notImplemented('getPod'),
  createPod: () => notImplemented('createPod'),
  updatePod: () => notImplemented('updatePod'),
  deletePod: () => notImplemented('deletePod'),
  listCategories: () => notImplemented('listCategories'),
  listProjects: () => notImplemented('listProjects'),
  listAgents: () => notImplemented('listAgents'),
  createAgent: () => notImplemented('createAgent'),
  updateAgent: () => notImplemented('updateAgent'),
  deleteAgent: () => notImplemented('deleteAgent'),
  listPodAgentIds: () => notImplemented('listPodAgentIds'),
  setPodAgents: () => notImplemented('setPodAgents'),
  setAgentPods: () => notImplemented('setAgentPods'),
}
