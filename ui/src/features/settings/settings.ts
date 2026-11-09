export type AppSettings = {
  emailNotifications: boolean
  weeklyDigest: boolean
  compactCards: boolean
  reduceMotion: boolean
}

export const defaultSettings: AppSettings = {
  emailNotifications: true,
  weeklyDigest: false,
  compactCards: false,
  reduceMotion: false,
}

const STORAGE_KEY = 'pods.settings'

export function loadSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultSettings
    const parsed = JSON.parse(raw) as Partial<AppSettings>
    return { ...defaultSettings, ...parsed }
  } catch {
    return defaultSettings
  }
}

export function saveSettings(settings: AppSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch {
    // Storage can be unavailable (private mode); settings still work in memory.
  }
}
