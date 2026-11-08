import { useState } from 'react'
import { Header } from './components/Header'
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

  return (
    <div className="app">
      <Header onHome={() => setRoute({ name: 'list' })} />

      <main className="app-main">
        {route.name === 'list' && (
          <PodList
            onCreate={() => setRoute({ name: 'create' })}
            onOpen={(id) => setRoute({ name: 'detail', id })}
          />
        )}

        {route.name === 'detail' && (
          <PodDetail
            id={route.id}
            onBack={() => setRoute({ name: 'list' })}
            onEdit={(id) => setRoute({ name: 'edit', id })}
          />
        )}

        {route.name === 'create' && (
          <PodForm
            mode="create"
            onDone={(id) => setRoute({ name: 'detail', id })}
            onCancel={() => setRoute({ name: 'list' })}
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
  )
}
