import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../test/server";
import { API, PEMILIK, renderApp } from "../../test/render";

const ID = "aaaaaaaa-0000-0000-0000-000000000001";
const SIKLUS = "bbbbbbbb-0000-0000-0000-000000000001";

const kandang = {
  id: ID,
  pemilik_id: PEMILIK.id,
  nama: "Kandang Utama",
  lokasi: "Blok 1",
  status: "AKTIF",
  siklus_aktif_id: SIKLUS,
  siklus_aktif_status: "AKTIF",
  status_alat: "ONLINE",
};

function stubDasar() {
  server.use(
    http.get(`${API}/auth/me`, () => HttpResponse.json(PEMILIK)),
    http.get(`${API}/notifikasi`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } })),
  );
}

function stubDetail(tambahan: Parameters<typeof server.use> = []) {
  stubDasar();
  server.use(
    http.get(`${API}/kandang/${ID}`, () => HttpResponse.json(kandang)),
    http.get(`${API}/kandang/${ID}/alat`, () =>
      HttpResponse.json({
        id: "cc",
        kandang_id: ID,
        status: "ONLINE",
        versi_jadwal_aktif: 1,
        waktu_terakhir_sinkron: "2026-11-01T10:00:00Z",
        wadah: [
          { id: "w2", nomor_wadah: 2, jumlah_stok: 50, ambang_menipis: 10, bahan_pakan_id: "b2", nama_bahan: "Jagung" },
          { id: "w1", nomor_wadah: 1, jumlah_stok: 5, ambang_menipis: 10, bahan_pakan_id: "b1", nama_bahan: "Dedak" },
        ],
      }),
    ),
    http.get(`${API}/kandang/${ID}/stok`, () =>
      HttpResponse.json([
        { id: "s1", wadah_id: "w1", nama_bahan: "Dedak", jumlah_estimasi: 5, ambang_menipis: 10 },
        { id: "s2", wadah_id: "w2", nama_bahan: "Jagung", jumlah_estimasi: 20000, ambang_menipis: 10 },
      ]),
    ),
    http.get(`${API}/kandang/${ID}/siklus/aktif`, () =>
      HttpResponse.json({
        id: SIKLUS,
        kandang_id: ID,
        jenis_ayam_id: "j1",
        fase_id: "f1",
        jumlah_ayam: 1000,
        status: "AKTIF",
        tanggal_mulai: "2026-10-01",
      }),
    ),
    http.get(`${API}/jenis-ayam/j1`, () => HttpResponse.json({ id: "j1", pemilik_id: PEMILIK.id, nama: "Broiler" })),
    http.get(`${API}/fase/f1`, () =>
      HttpResponse.json({ id: "f1", jenis_ayam_id: "j1", nama: "Starter", umur_min_hari: 0, umur_max_hari: 14 }),
    ),
    http.get(`${API}/siklus/${SIKLUS}/populasi`, () =>
      HttpResponse.json([
        { id: "p1", siklus_id: SIKLUS, jenis: "MORTALITAS", jumlah: 3, tanggal: "2026-10-05", catatan: "Panas" },
      ]),
    ),
  );
  // use() menaruh handler baru di depan, jadi yang ini menimpa handler bawaan di atas.
  server.use(...tambahan);
}

describe("detail kandang", () => {
  it("menampilkan alat, wadah berurutan, stok menipis, siklus, dan populasi", async () => {
    stubDetail();
    renderApp(`/kandang/${ID}`, { masuk: true });
    expect(await screen.findByRole("heading", { name: "Kandang Utama" })).toBeInTheDocument();
    expect(await screen.findByText("Online")).toBeInTheDocument();
    const wadah = await screen.findAllByText(/^Wadah \d$/);
    expect(wadah.map((e) => e.textContent)).toEqual(["Wadah 1", "Wadah 2"]);
    expect(await screen.findAllByText("Menipis")).toHaveLength(1);
    // stok bersatuan gram di server; ditampilkan sebagai g atau kg
    expect(await screen.findByText("5 g")).toBeInTheDocument();
    expect(await screen.findByText("20 kg")).toBeInTheDocument();
    expect(await screen.findByText("Broiler")).toBeInTheDocument();
    expect(await screen.findByText("Starter")).toBeInTheDocument();
    expect(await screen.findByText(/Mortalitas/)).toBeInTheDocument();
  });

  it("kandang kosong tanpa alat dan siklus menampilkan keadaan kosong", async () => {
    stubDetail([
      http.get(`${API}/kandang/${ID}/alat`, () => HttpResponse.json(null)),
      http.get(`${API}/kandang/${ID}/stok`, () => HttpResponse.json([])),
      http.get(`${API}/kandang/${ID}/siklus/aktif`, () => HttpResponse.json(null)),
    ]);
    renderApp(`/kandang/${ID}`, { masuk: true });
    expect(await screen.findByText("Belum ada alat")).toBeInTheDocument();
    expect(await screen.findByText("Belum ada stok")).toBeInTheDocument();
    expect(await screen.findByText("Kandang kosong")).toBeInTheDocument();
  });

  it("kandang yang tidak ada (404) menampilkan pesan tidak ditemukan", async () => {
    stubDasar();
    server.use(http.get(`${API}/kandang/${ID}`, () => HttpResponse.json({ detail: "Kandang tidak ditemukan" }, { status: 404 })));
    renderApp(`/kandang/${ID}`, { masuk: true });
    expect(await screen.findByText("Kandang tidak ditemukan")).toBeInTheDocument();
  });

  it("galat pada satu bagian tidak menyembunyikan bagian lain dan dapat diulang", async () => {
    const user = userEvent.setup();
    let n = 0;
    stubDetail([
      http.get(`${API}/kandang/${ID}/stok`, () => {
        n += 1;
        return n === 1
          ? HttpResponse.json({ detail: "boom" }, { status: 500 })
          : HttpResponse.json([{ id: "s1", wadah_id: "w1", nama_bahan: "Dedak", jumlah_estimasi: 20, ambang_menipis: 10 }]);
      }),
    ]);
    renderApp(`/kandang/${ID}`, { masuk: true });
    expect(await screen.findByRole("alert")).toHaveTextContent("Terjadi kesalahan di server");
    expect(await screen.findByText("Broiler")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Coba lagi" }));
    expect(await screen.findByText("20 g")).toBeInTheDocument();
  });

  it("kartu di dashboard membuka detail kandang", async () => {
    const user = userEvent.setup();
    stubDetail([
      http.get(`${API}/kandang`, () => HttpResponse.json([kandang], { headers: { "X-Total-Count": "1" } })),
    ]);
    renderApp("/", { masuk: true });
    await user.click(await screen.findByRole("link", { name: "Kandang Utama" }));
    expect(await screen.findByText("Alat dan wadah")).toBeInTheDocument();
  });
});
