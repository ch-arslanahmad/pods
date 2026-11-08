import { seedAgents, seedPods } from './seed'
import type {
  Agent,
  CreateAgentInput,
  CreatePodInput,
  ListPodsParams,
  Pod,
  PodPage,
  PodsContract,
  UpdateAgentPatch,
  UpdatePodPatch,
} from './types'

// Artificial latency keeps loading states visible during development.
const LATENCY_MS = 220

function delay(ms = LATENCY_MS): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms + Math.random() * 120))
}

let pods: Pod[] = seedPods.map((pod) => ({ ...pod }))
let agents: Agent[] = seedAgents.map((agent) => ({
  ...agent,
  pod_ids: [...agent.pod_ids],
}))
let nextId = Math.max(...pods.map((pod) => pod.id)) + 1
let nextAgentId = Math.max(...agents.map((agent) => agent.id)) + 1

const activePods = (): Pod[] => pods.filter((pod) => pod.deleted_at === null)

function day(value: string): string {
  const date = new Date(value.includes('T') ? value : value.replace(' ', 'T'))
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const dayOfMonth = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${dayOfMonth}`
}

function matchesQuery(pod: Pod, query: string): boolean {
  const needle = query.toLowerCase()
  return [pod.pod_name, pod.content, pod.category, pod.project ?? ''].some(
    (value) => value.toLowerCase().includes(needle),
  )
}

function findActive(id: number): Pod {
  const pod = activePods().find((candidate) => candidate.id === id)
  if (!pod) {
    throw new Error(`Pod ${id} not found`)
  }
  return pod
}

function findAgent(id: number): Agent {
  const agent = agents.find((candidate) => candidate.id === id)
  if (!agent) {
    throw new Error(`Agent ${id} not found`)
  }
  return agent
}

export const seedClient: PodsContract = {
  async ping() {
    await delay(120)
    return { status: 'pong' }
  },

  async listPods(params: ListPodsParams): Promise<PodPage> {
    await delay()

    const {
      query,
      category,
      project,
      created_after,
      created_before,
      limit = 50,
      offset = 0,
    } = params

    let result = activePods()

    if (query?.trim()) {
      result = result.filter((pod) => matchesQuery(pod, query.trim()))
    }
    if (category) {
      result = result.filter((pod) => pod.category === category)
    }
    if (project) {
      result = result.filter((pod) => pod.project === project)
    }
    if (created_after) {
      result = result.filter((pod) => day(pod.created_at) >= created_after)
    }
    if (created_before) {
      result = result.filter((pod) => day(pod.created_at) <= created_before)
    }

    const total = result.length
    const ordered = [...result].sort((a, b) =>
      b.created_at.localeCompare(a.created_at),
    )
    const page = ordered.slice(offset, offset + limit)

    return { pods: page.map((pod) => ({ ...pod })), total }
  },

  async getPod(id: number): Promise<Pod> {
    await delay()
    return { ...findActive(id) }
  },

  async createPod(input: CreatePodInput): Promise<Pod> {
    await delay()
    const now = new Date().toISOString()
    const pod: Pod = {
      id: nextId,
      pod_name: input.pod_name,
      content: input.content,
      category: input.category,
      project: input.project ?? null,
      created_at: now,
      updated_at: now,
      deleted_at: null,
    }
    nextId += 1
    pods = [...pods, pod]
    return { ...pod }
  },

  async updatePod(id: number, patch: UpdatePodPatch): Promise<Pod> {
    await delay()
    const current = findActive(id)
    const updated: Pod = {
      ...current,
      ...patch,
      updated_at: new Date().toISOString(),
    }
    pods = pods.map((pod) => (pod.id === id ? updated : pod))
    return { ...updated }
  },

  async deletePod(id: number): Promise<void> {
    await delay()
    const current = findActive(id)
    const now = new Date().toISOString()
    const updated: Pod = { ...current, updated_at: now, deleted_at: now }
    pods = pods.map((pod) => (pod.id === id ? updated : pod))
    agents = agents.map((agent) => ({
      ...agent,
      pod_ids: agent.pod_ids.filter((podId) => podId !== id),
    }))
  },

  async listCategories(): Promise<string[]> {
    await delay(120)
    return [...new Set(activePods().map((pod) => pod.category))].sort()
  },

  async listProjects(): Promise<string[]> {
    await delay(120)
    return [
      ...new Set(
        activePods()
          .map((pod) => pod.project)
          .filter((project): project is string => project !== null),
      ),
    ].sort()
  },

  async listAgents(): Promise<Agent[]> {
    await delay(160)
    return agents.map((agent) => ({ ...agent, pod_ids: [...agent.pod_ids] }))
  },

  async createAgent(input: CreateAgentInput): Promise<Agent> {
    await delay()
    const agent: Agent = {
      id: nextAgentId,
      ...input,
      created_at: new Date().toISOString(),
      pod_ids: [],
    }
    nextAgentId += 1
    agents = [...agents, agent]
    return { ...agent, pod_ids: [] }
  },

  async updateAgent(id: number, patch: UpdateAgentPatch): Promise<Agent> {
    await delay()
    const current = findAgent(id)
    const updated: Agent = { ...current, ...patch }
    agents = agents.map((agent) => (agent.id === id ? updated : agent))
    return { ...updated, pod_ids: [...updated.pod_ids] }
  },

  async deleteAgent(id: number): Promise<void> {
    await delay()
    findAgent(id)
    agents = agents.filter((agent) => agent.id !== id)
  },

  async listPodAgentIds(podId: number): Promise<number[]> {
    await delay(120)
    return agents
      .filter((agent) => agent.pod_ids.includes(podId))
      .map((agent) => agent.id)
  },

  async setPodAgents(podId: number, agentIds: number[]): Promise<void> {
    await delay()
    const selected = new Set(agentIds)
    agents = agents.map((agent) => {
      const connected = agent.pod_ids.includes(podId)
      if (selected.has(agent.id) && !connected) {
        return { ...agent, pod_ids: [...agent.pod_ids, podId] }
      }
      if (!selected.has(agent.id) && connected) {
        return {
          ...agent,
          pod_ids: agent.pod_ids.filter((id) => id !== podId),
        }
      }
      return agent
    })
  },

  async setAgentPods(agentId: number, podIds: number[]): Promise<void> {
    await delay()
    findAgent(agentId)
    agents = agents.map((agent) =>
      agent.id === agentId
        ? { ...agent, pod_ids: [...new Set(podIds)] }
        : agent,
    )
  },
}
