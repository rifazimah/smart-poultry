import { ApiError, layakDiulang, pesanGalat } from "./errors";

describe("pesanGalat", () => {
  it("memakai detail string dari server untuk 400/403/404/409", () => {
    expect(pesanGalat(new ApiError(409, "Alat sedang OFFLINE"))).toBe("Alat sedang OFFLINE");
    expect(pesanGalat(new ApiError(403, "User nonaktif"))).toBe("User nonaktif");
    expect(pesanGalat(new ApiError(400, "Total proporsi harus 1.0"))).toBe("Total proporsi harus 1.0");
    expect(pesanGalat(new ApiError(404, null))).toBe("Data tidak ditemukan.");
  });

  it("422 menampilkan nama field dan pesannya", () => {
    const detail = [
      { loc: ["body", "jumlah_ayam"], msg: "Input should be greater than 0" },
      { loc: ["query", "limit"], msg: "Input should be less than or equal to 100" },
    ];
    expect(pesanGalat(new ApiError(422, detail))).toBe(
      "jumlah_ayam: Input should be greater than 0; limit: Input should be less than or equal to 100",
    );
    expect(pesanGalat(new ApiError(422, undefined))).toBe("Data yang dikirim tidak valid.");
  });

  it("429 memakai pesan server atau Retry-After", () => {
    expect(pesanGalat(new ApiError(429, "Terlalu banyak percobaan login yang gagal. Coba lagi dalam 120 detik."))).toContain("120 detik");
    expect(pesanGalat(new ApiError(429, null, 45))).toBe("Terlalu banyak percobaan. Coba lagi dalam 45 detik.");
  });

  it("401 tanpa detail dan 5xx", () => {
    expect(pesanGalat(new ApiError(401, null))).toBe("Sesi Anda berakhir. Silakan masuk kembali.");
    expect(pesanGalat(new ApiError(503, "x"))).toMatch(/kesalahan di server/);
  });

  it("galat jaringan dan tak dikenal", () => {
    expect(pesanGalat(new TypeError("Failed to fetch"))).toMatch(/Tidak dapat terhubung/);
    expect(pesanGalat("apa saja")).toBe("Terjadi kesalahan tak terduga.");
  });
});

describe("ApiError.dariRespons", () => {
  it("membaca detail dan Retry-After", () => {
    const res = new Response("{}", { status: 429, headers: { "Retry-After": "90" } });
    const err = ApiError.dariRespons(res, { detail: "pelan-pelan" });
    expect(err.status).toBe(429);
    expect(err.detail).toBe("pelan-pelan");
    expect(err.retryAfter).toBe(90);
  });

  it("Retry-After tidak valid diabaikan", () => {
    const res = new Response("{}", { status: 429, headers: { "Retry-After": "besok" } });
    expect(ApiError.dariRespons(res, {}).retryAfter).toBeNull();
  });
});

describe("layakDiulang", () => {
  it("hanya galat server/jaringan/429 yang diulang otomatis", () => {
    expect(layakDiulang(new ApiError(500, null))).toBe(true);
    expect(layakDiulang(new ApiError(429, null))).toBe(true);
    expect(layakDiulang(new TypeError("net"))).toBe(true);
    expect(layakDiulang(new ApiError(403, null))).toBe(false);
    expect(layakDiulang(new ApiError(409, null))).toBe(false);
    expect(layakDiulang(new ApiError(422, null))).toBe(false);
  });
});
