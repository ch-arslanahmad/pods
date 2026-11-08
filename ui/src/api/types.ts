// The single source of truth for the UI. Screens import these types and the
// `api` object from `./client` — never a concrete transport.

export type Pod = {
  id: number
  pod_name: string
  category: string
  content: string
  project: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export type ListPodsParams = {
  query?: string
  category?: string
  project?: string
  created_after?: string
  created_before?: string
  limit?: number
  offset?: number
}

export type CreatePodInput = {
  pod_name: string
  content: string
  category: string
  project?: string | null
}

export type UpdatePodPatch = Partial<
  Pick<Pod, 'pod_name' | 'content' | 'category' | 'project'>
>

export type PodPage = {
  pods: Pod[]
  total: number
}

export type AgentStatus = 'active' | 'paused'

export type Agent = {
  id: number
  name: string
  description: string
  provider: string
  model: string
  status: AgentStatus
  created_at: string
  pod_ids: number[]
}

export type CreateAgentInput = {
  name: string
  description: string
  provider: string
  model: string
  status: AgentStatus
}

export type UpdateAgentPatch = Partial<CreateAgentInput>

export type PodsContract = {
  ping(): Promise<{ status: string }>
  listPods(params: ListPodsParams): Promise<PodPage>
  getPod(id: number): Promise<Pod>
  createPod(input: CreatePodInput): Promise<Pod>
  updatePod(id: number, patch: UpdatePodPatch): Promise<Pod>
  deletePod(id: number): Promise<void>
  listCategories(): Promise<string[]>
  listProjects(): Promise<string[]>
  listAgents(): Promise<Agent[]>
  createAgent(input: CreateAgentInput): Promise<Agent>
  updateAgent(id: number, patch: UpdateAgentPatch): Promise<Agent>
  deleteAgent(id: number): Promise<void>
  listPodAgentIds(podId: number): Promise<number[]>
  setPodAgents(podId: number, agentIds: number[]): Promise<void>
  setAgentPods(agentId: number, podIds: number[]): Promise<void>
}
