/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_MODE?: 'seed' | 'http'
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
