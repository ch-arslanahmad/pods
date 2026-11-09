import { httpClient } from './http'
import { seedClient } from './seedClient'
import type { PodsContract } from './types'

// The only switch between fake and real data. Screens import `api` from here.
const mode = import.meta.env.VITE_API_MODE ?? 'seed'

export const api: PodsContract = mode === 'http' ? httpClient : seedClient
