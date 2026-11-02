import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../test/server";
import { API, PEMILIK, renderApp } from "../../test/render";

const PEKERJA = { ...PEMILIK, id: "22222222-2222-2222-2222-222222222222", nama: "Budi", role: "PEKERJA" };
const PID = PEMILIK.id;

const protein = { id: "n1", pemilik_id: PID, nama: "Protein", satuan: "%", tipe_batas: "MIN_MAKS" };
const energi = { id: "n2", pemilik_id: PID, nama: "Energi", satuan: "kkal/kg", tipe_batas: "MINIMUM" };
const jagung = { id: "b1", pemilik_id: PID, nama: "Jagung", harga: 5000, batas_maksimum: 0.4, status_sistem: "DI_DALAM_SISTEM" };
const broiler = { id: "j1", pemilik_id: PID, nama: "Broiler" };
const starter = { id: "f1", jenis_ayam_id: "j1", nama: "Starter", umur_min_hari: 0, umur_max_hari: 14 };

function stub(tambahan: Parameters<typeof server.use> = [], pengguna = PEMILIK) {
  server.use(
    http.get(`${API}/auth/me`, () => HttpResponse.json(pengguna)),
    http.get(`${API}/notifikasi`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } })),
    http.get(`${API}/nutrisi`, () => HttpResponse.json([protein, energi])),
    http.get(`${API}/bahan-pakan`, () => HttpResponse.json([jagung])),
    http.get(`${API}/jenis-ayam`, () => HttpResponse.json([broiler])),
  );
  server.use(...tambahan);
}

async function bukaTab(user: ReturnType<typeof userEvent.setup>, nama: string) {
  await user.click(await screen.findByRole("tab", { name: nama }));
}

describe("master data: akses", () => {
  it("Pekerja tidak melihat menu dan diarahkan keluar", async () => {
    stub([http.get(`${API}/kandang`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } }))], PEKERJA);
    renderApp("/master-data", { masuk: true });
    expect(await screen.findByText("Halo, Budi")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Master data" })).not.toBeInTheDocument();
  });

  it("Pemilik melihat menu Master data", async () => {
    stub();
    renderApp("/master-data", { masuk: true });
    expect(await screen.findByRole("heading", { name: "Master data" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Master data" }).length).toBeGreaterThan(0);
  });
});

describe("master data: nutrisi", () => {
  it("menambah nutrisi mengirim body yang benar", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub([
      http.post(`${API}/nutrisi`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...protein, id: "n9" }, { status: 201 });
      }),
    ]);
    renderApp("/master-data", { masuk: true });
    await bukaTab(user, "Nutrisi");
    expect(await screen.findByText("Energi")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tambah nutrisi" }));
    const dialog = await screen.findByRole("dialog", { name: "Tambah nutrisi" });
    await user.type(within(dialog).getByLabelText("Nama"), "Kalsium");
    await user.type(within(dialog).getByLabelText("Satuan"), "%");
    await user.selectOptions(within(dialog).getByLabelText("Jenis batas"), "MINIMUM");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Nutrisi disimpan")).toBeInTheDocument();
    expect(body).toEqual({ nama: "Kalsium", satuan: "%", tipe_batas: "MINIMUM" });
  });

  it("hapus nutrisi yang masih dipakai menampilkan alasan dari server di dalam dialog", async () => {
    const user = userEvent.setup();
    stub([
      http.delete(`${API}/nutrisi/n1`, () =>
        HttpResponse.json({ detail: "Nutrisi masih dipakai oleh 2 bahan" }, { status: 409 }),
      ),
    ]);
    renderApp("/master-data", { masuk: true });
    await bukaTab(user, "Nutrisi");
    await user.click(await screen.findByRole("button", { name: "Hapus Protein" }));
    const dialog = await screen.findByRole("dialog", { name: "Hapus data?" });
    await user.click(within(dialog).getByRole("button", { name: "Hapus" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Nutrisi masih dipakai oleh 2 bahan");
  });
});

describe("master data: bahan pakan", () => {
  it("batas maksimum di atas 1 ditolak di klien tanpa request", async () => {
    const user = userEvent.setup();
    let dikirim = 0;
    stub([
      http.post(`${API}/bahan-pakan`, () => {
        dikirim += 1;
        return HttpResponse.json(jagung, { status: 201 });
      }),
    ]);
    renderApp("/master-data", { masuk: true });
    await bukaTab(user, "Bahan pakan");
    await user.click(await screen.findByRole("button", { name: "Tambah bahan" }));
    const dialog = await screen.findByRole("dialog", { name: "Tambah bahan pakan" });
    await user.type(within(dialog).getByLabelText("Nama"), "Dedak");
    await user.type(within(dialog).getByLabelText("Batas maksimum dalam campuran"), "40");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("pecahan 0 sampai 1");
    expect(dikirim).toBe(0);
  });

  it("mengubah bahan mengirim PATCH dengan angka", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub([
      http.patch(`${API}/bahan-pakan/b1`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(jagung);
      }),
    ]);
    renderApp("/master-data", { masuk: true });
    await bukaTab(user, "Bahan pakan");
    await user.click(await screen.findByRole("button", { name: "Ubah Jagung" }));
    const dialog = await screen.findByRole("dialog", { name: "Ubah bahan pakan" });
    const harga = within(dialog).getByLabelText("Harga per kg (Rp)");
    await user.clear(harga);
    await user.type(harga, "5500,5");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Bahan pakan disimpan")).toBeInTheDocument();
    expect(body).toEqual({ nama: "Jagung", harga: 5500.5, batas_maksimum: 0.4, status_sistem: "DI_DALAM_SISTEM" });
  });

  it("kandungan nutrisi: memuat nilai yang ada dan menyimpan seluruh daftar", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub([
      http.get(`${API}/bahan-pakan/b1/nutrisi`, () =>
        HttpResponse.json([
          { id: "k1", bahan_pakan_id: "b1", nutrisi_id: "n1", nilai_per_kg: 8.5, nama_nutrisi: "Protein", satuan: "%" },
        ]),
      ),
      http.put(`${API}/bahan-pakan/b1/nutrisi`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json([]);
      }),
    ]);
    renderApp("/master-data", { masuk: true });
    await bukaTab(user, "Bahan pakan");
    await user.click(await screen.findByRole("button", { name: "Kandungan Jagung" }));
    const dialog = await screen.findByRole("dialog", { name: /Kandungan nutrisi: Jagung/ });
    const proteinInput = await within(dialog).findByLabelText(/Protein/);
    expect(proteinInput).toHaveValue("8.5");
    await user.type(within(dialog).getByLabelText(/Energi/), "3300");
    await user.click(within(dialog).getByRole("button", { name: "Simpan kandungan" }));
    expect(await screen.findByText("Kandungan nutrisi disimpan")).toBeInTheDocument();
    expect(body).toEqual([
      { nutrisi_id: "n1", nilai_per_kg: 8.5 },
      { nutrisi_id: "n2", nilai_per_kg: 3300 },
    ]);
  });
});

describe("master data: jenis ayam", () => {
  it("salin dari template mengirim nama opsional", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub([
      http.get(`${API}/template/jenis-ayam`, () =>
        HttpResponse.json([{ id: "t1", nama: "Broiler Standar", deskripsi: "Ayam pedaging", fase: [{}, {}] }]),
      ),
      http.post(`${API}/template/jenis-ayam/t1/salin`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...broiler, id: "j2", nama: "Broiler Kita" }, { status: 201 });
      }),
    ]);
    renderApp("/master-data", { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Salin dari template" }));
    const dialog = await screen.findByRole("dialog", { name: "Salin dari template" });
    expect(await within(dialog).findByText("Broiler Standar")).toBeInTheDocument();
    await user.type(within(dialog).getByLabelText("Nama baru (opsional)"), "Broiler Kita");
    await user.click(within(dialog).getByRole("button", { name: "Salin Broiler Standar" }));
    expect(await screen.findByText('Jenis ayam "Broiler Kita" dibuat')).toBeInTheDocument();
    expect(body).toEqual({ nama: "Broiler Kita" });
  });

  it("detail: menambah fase, memvalidasi umur, dan menyimpan kebutuhan serta standar konsumsi", async () => {
    const user = userEvent.setup();
    let fase: unknown;
    let kebutuhan: unknown;
    let standar: unknown;
    stub([
      http.get(`${API}/jenis-ayam/j1`, () => HttpResponse.json(broiler)),
      http.get(`${API}/jenis-ayam/j1/fase`, () => HttpResponse.json([starter])),
      http.post(`${API}/jenis-ayam/j1/fase`, async ({ request }) => {
        fase = await request.json();
        return HttpResponse.json({ ...starter, id: "f2" }, { status: 201 });
      }),
      http.get(`${API}/fase/f1/kebutuhan-nutrisi`, () => HttpResponse.json([])),
      http.put(`${API}/fase/f1/kebutuhan-nutrisi`, async ({ request }) => {
        kebutuhan = await request.json();
        return HttpResponse.json([]);
      }),
      http.get(`${API}/fase/f1/standar-konsumsi`, () => HttpResponse.json(null)),
      http.put(`${API}/fase/f1/standar-konsumsi`, async ({ request }) => {
        standar = await request.json();
        return HttpResponse.json({ id: "s1", fase_id: "f1", ...(standar as object) });
      }),
    ]);
    renderApp("/master-data/jenis-ayam/j1", { masuk: true });
    expect(await screen.findByRole("heading", { name: "Broiler" })).toBeInTheDocument();
    expect(await screen.findByText("Umur 0–14 hari")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Tambah fase" }));
    let dialog = await screen.findByRole("dialog", { name: "Tambah fase" });
    await user.type(within(dialog).getByLabelText("Nama"), "Grower");
    await user.type(within(dialog).getByLabelText("Umur awal (hari)"), "30");
    await user.type(within(dialog).getByLabelText("Umur akhir (hari)"), "15");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Umur awal tidak boleh melebihi umur akhir");
    expect(fase).toBeUndefined();
    const akhir = within(dialog).getByLabelText("Umur akhir (hari)");
    await user.clear(akhir);
    await user.type(akhir, "35");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Fase disimpan")).toBeInTheDocument();
    expect(fase).toEqual({ nama: "Grower", umur_min_hari: 30, umur_max_hari: 35 });

    await user.click(screen.getByRole("button", { name: "Atur nutrisi Starter" }));
    dialog = await screen.findByRole("dialog", { name: /Nutrisi dan konsumsi: Starter/ });
    await user.type(await within(dialog).findByLabelText("Protein minimum"), "20");
    await user.type(within(dialog).getByLabelText("Protein maksimum"), "22");
    await user.click(within(dialog).getByRole("button", { name: "Simpan kebutuhan" }));
    expect(await screen.findByText("Kebutuhan nutrisi disimpan")).toBeInTheDocument();
    expect(kebutuhan).toEqual([{ nutrisi_id: "n1", batas_min: 20, batas_max: 22 }]);

    await user.type(await within(dialog).findByLabelText("Gram per ekor per hari"), "50");
    await user.type(within(dialog).getByLabelText("Frekuensi makan per hari"), "3");
    await user.type(within(dialog).getByLabelText("Durasi aduk (detik)"), "30");
    await user.type(within(dialog).getByLabelText("Volume air (liter)"), "2,5");
    await user.click(within(dialog).getByRole("button", { name: "Simpan standar" }));
    expect(await screen.findByText("Standar konsumsi disimpan")).toBeInTheDocument();
    expect(standar).toEqual({ gram_per_ekor_per_hari: 50, frekuensi_makan: 3, durasi_aduk: 30, volume_air: 2.5 });
  });

  it("jenis ayam yang tidak ada menampilkan pesan tidak ditemukan", async () => {
    stub([http.get(`${API}/jenis-ayam/zzz`, () => HttpResponse.json({ detail: "Tidak ditemukan" }, { status: 404 }))]);
    renderApp("/master-data/jenis-ayam/zzz", { masuk: true });
    expect(await screen.findByText("Jenis ayam tidak ditemukan")).toBeInTheDocument();
  });
});
