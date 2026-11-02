/**
 * Galat API dan pemetaannya ke pesan untuk pengguna (satu tempat untuk seluruh aplikasi).
 * Arti kode (lihat docs/spesifikasi/API_CONTRACT.md): 422 bentuk/nilai body salah, 400 nilai melanggar aturan,
 * 409 bertentangan dengan keadaan data, 429 terlalu banyak percobaan login.
 */

type Detail422 = { loc?: Array<string | number>; msg?: string };

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;
  /** Detik, dari header Retry-After (429). */
  readonly retryAfter: number | null;

  constructor(status: number, detail: unknown, retryAfter: number | null = null) {
    super(typeof detail === "string" ? detail : `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.retryAfter = retryAfter;
  }

  static dariRespons(response: Response, body: unknown): ApiError {
    const mentah = response.headers.get("Retry-After");
    const retry = mentah !== null && /^\d+$/.test(mentah) ? Number(mentah) : null;
    const detail = body && typeof body === "object" && "detail" in body ? (body as { detail: unknown }).detail : body;
    return new ApiError(response.status, detail, retry);
  }
}

function pesan422(detail: unknown): string {
  if (!Array.isArray(detail) || detail.length === 0) return "Data yang dikirim tidak valid.";
  return (detail as Detail422[])
    .map((d) => {
      const field = d.loc?.filter((x) => x !== "body" && x !== "query").join(".");
      return field ? `${field}: ${d.msg ?? "tidak valid"}` : (d.msg ?? "tidak valid");
    })
    .join("; ");
}

/** Pesan siap tampil untuk galat apa pun (ApiError, galat jaringan, atau lainnya). */
export function pesanGalat(err: unknown): string {
  if (err instanceof ApiError) {
    const teks = typeof err.detail === "string" ? err.detail : null;
    switch (true) {
      case err.status === 401:
        return teks ?? "Sesi Anda berakhir. Silakan masuk kembali.";
      case err.status === 422:
        return pesan422(err.detail);
      case err.status === 429:
        return teks ?? `Terlalu banyak percobaan. Coba lagi dalam ${err.retryAfter ?? 60} detik.`;
      case err.status >= 500:
        return "Terjadi kesalahan di server. Coba lagi sebentar lagi.";
      case err.status === 404:
        return teks ?? "Data tidak ditemukan.";
      default:
        return teks ?? `Permintaan gagal (HTTP ${err.status}).`;
    }
  }
  // fetch gagal terhubung (server mati, CORS, offline) melempar TypeError
  if (err instanceof TypeError) return "Tidak dapat terhubung ke server. Periksa koneksi Anda.";
  return "Terjadi kesalahan tak terduga.";
}

/** Galat 4xx (kecuali 408/429) tidak layak diulang otomatis. */
export function layakDiulang(err: unknown): boolean {
  if (err instanceof ApiError) return err.status >= 500 || err.status === 408 || err.status === 429;
  return true; // galat jaringan
}
