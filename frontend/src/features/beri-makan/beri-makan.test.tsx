import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../test/server";
import { API, PEMILIK, renderApp } from "../../test/render";

const KANDANG = "aaaaaaaa-0000-0000-0000-000000000001";
const SIKLUS = "bbbbbbbb-0000-0000-0000-000000000001";
const PEKERJA = { ...PEMILIK, id: "22222222-2222-2222-2222-222222222222", nama: "Budi", role: "PEKERJA" };

const perintah = (status: string, tipe = "BERI_MAKAN", id = "p1") => ({
  id,
  alat_id: "al",
  dibuat_oleh_id: PEMILIK.id,
  tipe,
  command_id: "c-" + id,
  status,
  formulasi_id: "f1",
  dibuat_pada: "2026-11-02T08:00:00Z",
});

const formulasiAktif = {
  id: "f1",
  siklus_id: SIKLUS,
  mode: "OTOMATIS",
  status: "VALID",
  aktif: true,
  total_biaya_per_kg: 6500,
  dibuat_oleh_id: PEMILIK.id,
  dibuat_pada: "2026-11-01T10:00:00Z",
};

const alat = (status: string) => ({
  id: "al",
  kandang_id: KANDANG,
  status,
  versi_jadwal_aktif: 1,
  waktu_terakhir_sinkron: null,
  wadah: [],
});

function stub(tambahan: Parameters<typeof server.use> = [], pengguna = PEMILIK) {
  server.use(
    http.get(`${API}/auth/me`, () => HttpResponse.json(pengguna)),
    http.get(`${API}/notifikasi`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } })),
    http.get(`${API}/kandang/${KANDANG}/siklus/aktif`, () =>
      HttpResponse.json({
        id: SIKLUS,
        kandang_id: KANDANG,
        jenis_ayam_id: "j1",
        fase_id: "f1",
        jumlah_ayam: 100,
        status: "AKTIF",
        tanggal_mulai: "2026-10-01",
      }),
    ),
    http.get(`${API}/kandang/${KANDANG}/alat`, () => HttpResponse.json(alat("ONLINE"))),
    http.get(`${API}/siklus/${SIKLUS}/formulasi`, () => HttpResponse.json([formulasiAktif])),
    http.get(`${API}/kandang/${KANDANG}/perintah`, () => HttpResponse.json([])),
  );
  server.use(...tambahan);
}

const halaman = `/kandang/${KANDANG}/beri-makan`;

describe("beri makan", () => {
  it("mengirim formulasi aktif dan menampilkan konfirmasi", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub([
      http.post(`${API}/kandang/${KANDANG}/perintah/beri-makan`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(perintah("PENDING"), { status: 201 });
      }),
    ]);
    renderApp(halaman, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Beri makan sekarang" }));
    expect(await screen.findByText("Perintah beri makan dikirim")).toBeInTheDocument();
    expect(body).toEqual({ formulasi_id: "f1" });
  });

  it("pekerja juga dapat memberi makan", async () => {
    stub([], PEKERJA);
    renderApp(halaman, { masuk: true });
    const tombol = await screen.findByRole("button", { name: "Beri makan sekarang" });
    await vi.waitFor(() => expect(tombol).toBeEnabled());
  });

  it("tombol nonaktif tanpa formulasi aktif", async () => {
    stub([http.get(`${API}/siklus/${SIKLUS}/formulasi`, () => HttpResponse.json([{ ...formulasiAktif, aktif: false }]))]);
    renderApp(halaman, { masuk: true });
    expect(await screen.findByText("Belum ada formulasi aktif untuk siklus ini.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Beri makan sekarang" })).toBeDisabled();
  });

  it("tombol nonaktif saat alat offline", async () => {
    stub([http.get(`${API}/kandang/${KANDANG}/alat`, () => HttpResponse.json(alat("OFFLINE")))]);
    renderApp(halaman, { masuk: true });
    expect(await screen.findByText("Alat sedang offline.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Beri makan sekarang" })).toBeDisabled();
  });

  it("tombol nonaktif saat ada perintah berjalan", async () => {
    stub([http.get(`${API}/kandang/${KANDANG}/perintah`, () => HttpResponse.json([perintah("BERJALAN")]))]);
    renderApp(halaman, { masuk: true });
    expect(await screen.findByText("Alat sedang memproses perintah.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Beri makan sekarang" })).toBeDisabled();
  });

  it("galat 409 dari server ditampilkan", async () => {
    const user = userEvent.setup();
    stub([
      http.post(`${API}/kandang/${KANDANG}/perintah/beri-makan`, () =>
        HttpResponse.json({ detail: "Stok tidak cukup: Jagung" }, { status: 409 }),
      ),
    ]);
    renderApp(halaman, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Beri makan sekarang" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Stok tidak cukup: Jagung");
  });

  it("riwayat dipoll sampai perintah selesai lalu berhenti", async () => {
    let panggilan = 0;
    stub([
      http.get(`${API}/kandang/${KANDANG}/perintah`, () => {
        panggilan += 1;
        return HttpResponse.json([perintah(panggilan < 3 ? "BERJALAN" : "SUKSES")]);
      }),
    ]);
    renderApp(halaman, { masuk: true });
    expect(await screen.findByText("Berjalan")).toBeInTheDocument();
    expect(await screen.findByText("Sukses")).toBeInTheDocument();
    const setelahSelesai = panggilan;
    await new Promise((r) => setTimeout(r, 300));
    expect(panggilan).toBe(setelahSelesai);
  });

  it("stop darurat meminta konfirmasi sebelum mengirim", async () => {
    const user = userEvent.setup();
    let dikirim = 0;
    stub([
      http.post(`${API}/kandang/${KANDANG}/perintah/stop-darurat`, () => {
        dikirim += 1;
        return HttpResponse.json(perintah("PENDING", "STOP_DARURAT", "p2"), { status: 201 });
      }),
    ]);
    renderApp(halaman, { masuk: true });
    await user.click(await screen.findByRole("button", { name: /Stop darurat/ }));
    await user.click(await screen.findByRole("button", { name: "Batal" }));
    expect(dikirim).toBe(0);
    await user.click(screen.getByRole("button", { name: /Stop darurat/ }));
    await user.click(await screen.findByRole("button", { name: "Ya, hentikan" }));
    expect(await screen.findByText("Stop darurat dikirim")).toBeInTheDocument();
    expect(dikirim).toBe(1);
  });
});
