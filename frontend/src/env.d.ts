/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Alamat backend tanpa /api/v1, mis. http://localhost:8000 */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
