import { useEffect, useState } from 'react'
import { Background } from './components/Background'
import { Header } from './components/Header'
import { Sidebar } from './components/Sidebar'
import { Agents } from './features/agents/Agents'
import { emptyFilters, type PodFilterState } from './features/pods/filters'
import { PodDetail } from './features/pods/PodDetail'
import { PodForm } from './features/pods/PodForm'
import { PodList } from './features/pods/PodList'
import { Settings, SignedOut } from './features/settings/Settings'
import {
  loadSettings,
  saveSettings,
  type AppSettings,
} from './features/settings/settings'

type Route =
  | { name: 'list' }
  | { name: 'detail'; id: number }
  | { name: 'create' }
  | { name: 'edit'; id: number }
  | { name: 'agents' }
  | { name: 'settings' }

export default function App() {
  const [route, setRoute] = useState<Route>({ name: 'list' })
  const [filters, setFilters] = useState<PodFilterState>(emptyFilters)
  const [offset, setOffset] = useState(0)
  const [settings, setSettings] = useState<AppSettings>(() => loadSettings())
  const [signedOut, setSignedOut] = useState(false)

  useEffect(() => {
    saveSettings(settings)
  }, [settings])

  const patchFilters = (patch: Partial<PodFilterState>) => {
    setFilters((current) => ({ ...current, ...patch }))
    setOffset(0)
  }

  const clearFilters = () => {
    setFilters(emptyFilters)
    setOffset(0)
  }

  const patchSettings = (patch: Partial<AppSettings>) => {
    setSettings((current) => ({ ...current, ...patch }))
  }

  const goHome = () => setRoute({ name: 'list' })

  const handleQueryChange = (query: string) => {
    patchFilters({ query })
    if (route.name !== 'list') {
      setRoute({ name: 'list' })
    }
  }

  if (signedOut) {
    return (
      <SignedOut
        onSignIn={() => {
          setSignedOut(false)
          setRoute({ name: 'list' })
        }}
      />
    )
  }

  const libraryActive =
    route.name === 'list' ||
    route.name === 'detail' ||
    route.name === 'create' ||
    route.name === 'edit'

  return (
    <div
      className="app"
      data-density={settings.compactCards ? 'compact' : 'comfortable'}
      data-motion={settings.reduceMotion ? 'reduced' : 'full'}
    >
      <Background />

      <Header
        query={filters.query}
        onQueryChange={handleQueryChange}
        onCreate={() => setRoute({ name: 'create' })}
        onHome={goHome}
        onAgents={() => setRoute({ name: 'agents' })}
        agentsActive={route.name === 'agents'}
      />

      <div className="shell">
        <Sidebar
          filters={filters}
          onChange={patchFilters}
          onClear={clearFilters}
          libraryActive={libraryActive}
          settingsActive={route.name === 'settings'}
          onSettings={() => setRoute({ name: 'settings' })}
        />

        <main className="content">
          {route.name === 'list' && (
            <PodList
              filters={filters}
              offset={offset}
              onOffsetChange={setOffset}
              onCreate={() => setRoute({ name: 'create' })}
              onClear={clearFilters}
              onOpen={(id) => setRoute({ name: 'detail', id })}
            />
          )}

          {route.name === 'detail' && (
            <PodDetail
              id={route.id}
              onBack={goHome}
              onEdit={(id) => setRoute({ name: 'edit', id })}
            />
          )}

          {route.name === 'create' && (
            <PodForm
              mode="create"
              onDone={(id) => setRoute({ name: 'detail', id })}
              onCancel={goHome}
            />
          )}

          {route.name === 'edit' && (
            <PodForm
              mode="edit"
              id={route.id}
              onDone={(id) => setRoute({ name: 'detail', id })}
              onCancel={() => setRoute({ name: 'detail', id: route.id })}
            />
          )}

          {route.name === 'agents' && <Agents onBack={goHome} />}

          {route.name === 'settings' && (
            <Settings
              settings={settings}
              onChange={patchSettings}
              onBack={goHome}
              onLogout={() => setSignedOut(true)}
            />
          )}
        </main>
      </div>
    </div>
  )
}
