import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../test/server";
import { API, PEMILIK, renderApp } from "../../test/render";

const KANDANG = "aaaaaaaa-0000-0000-0000-000000000001";
const SIKLUS = "bbbbbbbb-0000-0000-0000-000000000001";
const PEKERJA = { ...PEMILIK, id: "22222222-2222-2222-2222-222222222222", nama: "Budi", role: "PEKERJA" };

const preview = {
  siklus_id: SIKLUS,
  mode: "OTOMATIS",
  status: "VALID",
  pesan: null,
  total_biaya_per_kg: 6500,
  item: [
    { bahan_pakan_id: "b1", nama_bahan: "Jagung", proporsi: 0.6, berat_per_sesi: 3000 },
    { bahan_pakan_id: "b2", nama_bahan: "Dedak", proporsi: 0.4, berat_per_sesi: 2000 },
  ],
  nutrisi_hasil: [
    { nutrisi_id: "n1", nama_nutrisi: "Protein", nilai_hasil: 20, batas_min: 19, batas_max: null, keterangan: null, status: "SESUAI" },
  ],
};

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
    http.get(`${API}/siklus/${SIKLUS}/formulasi`, () => HttpResponse.json([])),
    http.get(`${API}/bahan-pakan`, () =>
      HttpResponse.json([
        { id: "b1", pemilik_id: PEMILIK.id, nama: "Jagung", harga: 5000, batas_maksimum: null, status_sistem: "AKTIF" },
        { id: "b2", pemilik_id: PEMILIK.id, nama: "Dedak", harga: 3000, batas_maksimum: null, status_sistem: "AKTIF" },
      ]),
    ),
  );
  server.use(...tambahan);
}

const halaman = `/kandang/${KANDANG}/formulasi`;

describe("formulasi", () => {
  it("hitung otomatis menampilkan resep dan nutrisi, lalu simpan mengirim preview apa adanya", async () => {
    const user = userEvent.setup();
    let tersimpan: unknown;
    stub([
      http.post(`${API}/siklus/${SIKLUS}/formulasi/otomatis`, () => HttpResponse.json(preview)),
      http.post(`${API}/formulasi`, async ({ request }) => {
        tersimpan = await request.json();
        return HttpResponse.json({ id: "f9", ...preview, aktif: false, dibuat_oleh_id: PEMILIK.id, dibuat_pada: "2026-11-02T00:00:00Z" }, { status: 201 });
      }),
    ]);
    renderApp(halaman, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Hitung otomatis" }));
    expect(await screen.findByText("Pratinjau (belum disimpan)")).toBeInTheDocument();
    expect(screen.getByText("Jagung")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
    expect(screen.getByText("Sesuai")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Simpan formulasi" }));
    expect((await screen.findAllByText("Formulasi tersimpan.")).length).toBeGreaterThan(0);
    expect(tersimpan).toEqual(preview);
  });

  it("hasil tidak sempurna menampilkan diagnosis dari server dan status nutrisi bermasalah", async () => {
    const user = userEvent.setup();
    stub([
      http.post(`${API}/siklus/${SIKLUS}/formulasi/otomatis`, () =>
        HttpResponse.json({
          ...preview,
          status: "TIDAK_SEMPURNA",
          item: [],
          pesan: "Formulasi tidak dapat memenuhi batas nutrisi: Protein (min 30; tertinggi yang mungkin 22)",
          nutrisi_hasil: [
            { nutrisi_id: "n1", nama_nutrisi: "Protein", nilai_hasil: 22, batas_min: 30, batas_max: null, keterangan: "Batas minimum 30 tidak tercapai", status: "KURANG" },
          ],
        }),
      ),
    ]);
    renderApp(halaman, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Hitung otomatis" }));
    expect(await screen.findByText("Tidak sempurna")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Protein (min 30; tertinggi yang mungkin 22)");
    expect(screen.getByText("Kurang")).toBeInTheDocument();
    expect(screen.getByText("Batas minimum 30 tidak tercapai")).toBeInTheDocument();
  });

  it("mode manual: tombol hitung baru aktif bila total 100% dan mengirim proporsi pecahan", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub([
      http.post(`${API}/siklus/${SIKLUS}/formulasi/manual`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...preview, mode: "MANUAL" });
      }),
    ]);
    renderApp(halaman, { masuk: true });
    await user.click(await screen.findByRole("radio", { name: "Manual" }));
    const hitung = await screen.findByRole("button", { name: "Hitung formulasi manual" });
    expect(hitung).toBeDisabled();
    await user.type(screen.getByLabelText("Jagung"), "70");
    expect(hitung).toBeDisabled();
    await user.type(screen.getByLabelText("Dedak"), "30");
    expect(hitung).toBeEnabled();
    await user.click(hitung);
    expect(await screen.findByText("Pratinjau (belum disimpan)")).toBeInTheDocument();
    expect(body).toEqual({
      item: [
        { bahan_pakan_id: "b1", proporsi: 0.7 },
        { bahan_pakan_id: "b2", proporsi: 0.3 },
      ],
    });
  });

  it("galat 400 dari server saat menghitung ditampilkan", async () => {
    const user = userEvent.setup();
    stub([
      http.post(`${API}/siklus/${SIKLUS}/formulasi/otomatis`, () =>
        HttpResponse.json({ detail: "Standar konsumsi fase belum diisi" }, { status: 400 }),
      ),
    ]);
    renderApp(halaman, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Hitung otomatis" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Standar konsumsi fase belum diisi");
  });

  it("riwayat menampilkan formulasi tersimpan dan detailnya dapat dibuka", async () => {
    const user = userEvent.setup();
    stub([
      http.get(`${API}/siklus/${SIKLUS}/formulasi`, () =>
        HttpResponse.json([
          { id: "f1", siklus_id: SIKLUS, mode: "OTOMATIS", status: "VALID", aktif: true, total_biaya_per_kg: 6500, dibuat_oleh_id: PEMILIK.id, dibuat_pada: "2026-11-01T10:00:00Z" },
        ]),
      ),
      http.get(`${API}/formulasi/f1`, () =>
        HttpResponse.json({ id: "f1", aktif: true, dibuat_oleh_id: PEMILIK.id, dibuat_pada: "2026-11-01T10:00:00Z", ...preview }),
      ),
    ]);
    renderApp(halaman, { masuk: true });
    const kartu = (await screen.findByText("Aktif")).closest("div")!.parentElement!;
    await user.click(within(kartu).getByRole("button", { name: "Lihat" }));
    expect(await screen.findByText("Jagung")).toBeInTheDocument();
  });

  it("kandang kosong tanpa siklus aktif tidak menawarkan pembuatan formulasi", async () => {
    stub([http.get(`${API}/kandang/${KANDANG}/siklus/aktif`, () => HttpResponse.json(null))]);
    renderApp(halaman, { masuk: true });
    expect(await screen.findByText("Kandang kosong")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Hitung otomatis" })).not.toBeInTheDocument();
  });

  it("Pekerja diarahkan keluar dari halaman formulasi", async () => {
    stub([http.get(`${API}/kandang`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } }))], PEKERJA);
    renderApp(halaman, { masuk: true });
    expect(await screen.findByText("Halo, Budi")).toBeInTheDocument();
    expect(screen.queryByText("Formulasi pakan")).not.toBeInTheDocument();
  });
});
