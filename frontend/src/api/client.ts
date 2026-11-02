import createClient, { type Middleware } from "openapi-fetch";
import { ambilToken } from "../auth/token";
import { API_BASE_URL } from "../lib/env";
import { ApiError } from "./errors";
import type { components, paths } from "./schema";

export type Skema = components["schemas"];

// `fetch` dibaca saat dipanggil (bukan saat klien dibuat) agar dapat diganti/di-mock, mis. oleh MSW pada test.
export const api = createClient<paths>({ baseUrl: API_BASE_URL, fetch: (request) => globalThis.fetch(request) });

let saatTakBerwenang: (() => void) | null = null;

/** AuthProvider mendaftarkan fungsi logout di sini; dipanggil bila server membalas 401 pada request terautentikasi. */
export function aturPenangananSesiBerakhir(fn: (() => void) | null): void {
  saatTakBerwenang = fn;
}

const middleware: Middleware = {
  onRequest({ request }) {
    const token = ambilToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
  onResponse({ request, response }) {
    // 401 pada /auth/login berarti kredensial salah, bukan sesi berakhir.
    if (response.status === 401 && !new URL(request.url).pathname.endsWith("/auth/login")) {
      saatTakBerwenang?.();
    }
    return undefined;
  },
};
api.use(middleware);

/** Hasil mentah openapi-fetch -> data bertipe, atau lempar ApiError. */
export async function ambil<T>(
  janji: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<{ data: T; response: Response }> {
  const { data, error, response } = await janji;
  if (!response.ok || error !== undefined) throw ApiError.dariRespons(response, error);
  return { data: data as T, response };
}

/** Total data (tanpa paginasi) dari header X-Total-Count. */
export function totalDariHeader(response: Response): number {
  const n = Number(response.headers.get("X-Total-Count"));
  return Number.isFinite(n) ? n : 0;
}
