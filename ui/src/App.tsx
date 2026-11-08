import { useState } from 'react'
import { Background } from './components/Background'
import { Header } from './components/Header'
import { Sidebar } from './components/Sidebar'
import { emptyFilters, type PodFilterState } from './features/pods/filters'
import { PodDetail } from './features/pods/PodDetail'
import { PodForm } from './features/pods/PodForm'
import { PodList } from './features/pods/PodList'

type Route =
  | { name: 'list' }
  | { name: 'detail'; id: number }
  | { name: 'create' }
  | { name: 'edit'; id: number }

export default function App() {
  const [route, setRoute] = useState<Route>({ name: 'list' })
  const [filters, setFilters] = useState<PodFilterState>(emptyFilters)
  const [offset, setOffset] = useState(0)

  const patchFilters = (patch: Partial<PodFilterState>) => {
    setFilters((current) => ({ ...current, ...patch }))
    setOffset(0)
  }

  const clearFilters = () => {
    setFilters(emptyFilters)
    setOffset(0)
  }

  const goHome = () => setRoute({ name: 'list' })

  const handleQueryChange = (query: string) => {
    patchFilters({ query })
    if (route.name !== 'list') {
      setRoute({ name: 'list' })
    }
  }

  return (
    <div className="app">
      <Background />

      <Header
        query={filters.query}
        onQueryChange={handleQueryChange}
        onCreate={() => setRoute({ name: 'create' })}
        onHome={goHome}
      />

      <div className="shell">
        <Sidebar
          filters={filters}
          onChange={patchFilters}
          onClear={clearFilters}
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
        </main>
      </div>
    </div>
  )
}
