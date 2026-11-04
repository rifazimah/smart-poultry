import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../test/server";
import { API, PEMILIK, renderApp } from "../../test/render";

const ID = "aaaaaaaa-0000-0000-0000-000000000001";
const SIKLUS = "bbbbbbbb-0000-0000-0000-000000000001";
const PEKERJA = { ...PEMILIK, id: "22222222-2222-2222-2222-222222222222", nama: "Budi", role: "PEKERJA" };

const kandang = { id: ID, pemilik_id: PEMILIK.id, nama: "Kandang Utama", lokasi: "Blok 1", status: "AKTIF", siklus_aktif_id: SIKLUS, siklus_aktif_status: "AKTIF", status_alat: "ONLINE" };
const siklus = { id: SIKLUS, kandang_id: ID, jenis_ayam_id: "j1", fase_id: "f1", jumlah_ayam: 100, status: "AKTIF", tanggal_mulai: "2026-10-01" };
const alat = {
  id: "al1",
  kandang_id: ID,
  status: "ONLINE",
  versi_jadwal_aktif: 1,
  waktu_terakhir_sinkron: null,
  wadah: [
    { id: "w1", nomor_wadah: 1, jumlah_stok: 5000, ambang_menipis: null, bahan_pakan_id: "b1", nama_bahan: "Jagung" },
    { id: "w2", nomor_wadah: 2, jumlah_stok: 2000, ambang_menipis: null, bahan_pakan_id: null, nama_bahan: null },
  ],
};
const stok = [
  { id: "s1", wadah_id: "w1", nama_bahan: "Jagung", jumlah_estimasi: 5000, ambang_menipis: null },
  { id: "s2", wadah_id: "w2", nama_bahan: "Dedak", jumlah_estimasi: 2000, ambang_menipis: null },
];

interface Opsi {
  pengguna?: typeof PEMILIK;
  alat?: typeof alat | null;
  siklus?: typeof siklus | null;
  tambahan?: Parameters<typeof server.use>;
}

function stub({ pengguna = PEMILIK, alat: a = alat, siklus: s = siklus, tambahan = [] }: Opsi = {}) {
  server.use(
    http.get(`${API}/auth/me`, () => HttpResponse.json(pengguna)),
    http.get(`${API}/notifikasi`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } })),
    http.get(`${API}/kandang`, () => HttpResponse.json([kandang], { headers: { "X-Total-Count": "1" } })),
    http.get(`${API}/kandang/${ID}`, () => HttpResponse.json(kandang)),
    http.get(`${API}/kandang/${ID}/alat`, () => HttpResponse.json(a)),
    http.get(`${API}/kandang/${ID}/stok`, () => HttpResponse.json(a ? stok : [])),
    http.get(`${API}/kandang/${ID}/siklus/aktif`, () => HttpResponse.json(s)),
    http.get(`${API}/siklus/${SIKLUS}/populasi`, () =>
      HttpResponse.json([{ id: "p1", siklus_id: SIKLUS, jenis: "MORTALITAS", jumlah: 3, tanggal: "2026-10-05", catatan: null }]),
    ),
    http.get(`${API}/jenis-ayam`, () => HttpResponse.json([{ id: "j1", pemilik_id: PEMILIK.id, nama: "Broiler" }])),
    http.get(`${API}/jenis-ayam/j1`, () => HttpResponse.json({ id: "j1", pemilik_id: PEMILIK.id, nama: "Broiler" })),
    http.get(`${API}/jenis-ayam/j1/fase`, () =>
      HttpResponse.json([
        { id: "f2", jenis_ayam_id: "j1", nama: "Grower", umur_min_hari: 15, umur_max_hari: 28 },
        { id: "f1", jenis_ayam_id: "j1", nama: "Starter", umur_min_hari: 0, umur_max_hari: 14 },
      ]),
    ),
    http.get(`${API}/fase/f1`, () => HttpResponse.json({ id: "f1", jenis_ayam_id: "j1", nama: "Starter", umur_min_hari: 0, umur_max_hari: 14 })),
    http.get(`${API}/bahan-pakan`, () =>
      HttpResponse.json([
        { id: "b1", pemilik_id: PEMILIK.id, nama: "Jagung", harga: 5000, batas_maksimum: null, status_sistem: "DI_DALAM_SISTEM" },
        { id: "b2", pemilik_id: PEMILIK.id, nama: "Dedak", harga: 3000, batas_maksimum: null, status_sistem: "DI_DALAM_SISTEM" },
      ]),
    ),
  );
  server.use(...tambahan);
}

const detail = `/kandang/${ID}`;
const galat = (pesan: string, status = 409) => HttpResponse.json({ detail: pesan }, { status });

describe("aksi kandang", () => {
  it("Pemilik menambah kandang dari dashboard lalu dibawa ke detailnya", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub({
      tambahan: [
        http.post(`${API}/kandang`, async ({ request }) => {
          body = await request.json();
          return HttpResponse.json({ id: ID, pemilik_id: PEMILIK.id, nama: "Kandang Utama", lokasi: null, status: "AKTIF" }, { status: 201 });
        }),
      ],
    });
    renderApp("/", { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Tambah kandang" }));
    const dialog = await screen.findByRole("dialog", { name: "Tambah kandang" });
    await user.type(within(dialog).getByLabelText("Nama kandang"), "Kandang Utama");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByRole("heading", { name: "Kandang Utama" })).toBeInTheDocument();
    expect(body).toEqual({ nama: "Kandang Utama", lokasi: null });
  });

  it("Pekerja tidak melihat tombol Tambah kandang", async () => {
    stub({ pengguna: PEKERJA });
    renderApp("/", { masuk: true });
    expect(await screen.findByText("Kandang Utama")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tambah kandang" })).not.toBeInTheDocument();
  });

  it("ubah dan nonaktifkan mengirim PATCH; hapus yang ditolak menampilkan alasan, hapus berhasil kembali ke dashboard", async () => {
    const user = userEvent.setup();
    const patch: unknown[] = [];
    let hapusKe = 0;
    stub({
      tambahan: [
        http.patch(`${API}/kandang/${ID}`, async ({ request }) => {
          patch.push(await request.json());
          return HttpResponse.json(kandang);
        }),
        http.delete(`${API}/kandang/${ID}`, () => {
          hapusKe += 1;
          return hapusKe === 1 ? galat("Kandang sudah punya siklus; nonaktifkan saja") : new HttpResponse(null, { status: 204 });
        }),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Ubah kandang" }));
    let dialog = await screen.findByRole("dialog", { name: "Ubah kandang" });
    const lokasi = within(dialog).getByLabelText("Lokasi");
    await user.clear(lokasi);
    await user.type(lokasi, "Blok 2");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Kandang disimpan")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Nonaktifkan" }));
    expect(await screen.findByText("Kandang dinonaktifkan")).toBeInTheDocument();
    expect(patch).toEqual([{ nama: "Kandang Utama", lokasi: "Blok 2" }, { status: "NONAKTIF" }]);

    await user.click(screen.getByRole("button", { name: "Hapus kandang" }));
    dialog = await screen.findByRole("dialog", { name: "Hapus data?" });
    await user.click(within(dialog).getByRole("button", { name: "Hapus" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("nonaktifkan saja");
    await user.click(within(dialog).getByRole("button", { name: "Hapus" }));
    expect(await screen.findByText("Kandang dihapus")).toBeInTheDocument();
    expect(await screen.findByText("Ringkasan kandang Anda.")).toBeInTheDocument();
  });
});

describe("aksi alat dan wadah", () => {
  it("daftarkan alat menampilkan token sekali, dan dialog bertahan walau daftar alat sudah dimuat ulang", async () => {
    const user = userEvent.setup();
    let terdaftar = false;
    stub({
      tambahan: [
        http.get(`${API}/kandang/${ID}/alat`, () => HttpResponse.json(terdaftar ? { ...alat, wadah: [] } : null)),
        http.post(`${API}/kandang/${ID}/alat`, () => {
          terdaftar = true;
          return HttpResponse.json({ id: "al1", kandang_id: ID, status: "OFFLINE", device_token: "tok-rahasia-123" }, { status: 201 });
        }),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Daftarkan alat" }));
    const dialog = await screen.findByRole("dialog", { name: "Token alat" });
    // tombol Daftarkan alat sudah hilang (alat terdaftar), tetapi token tetap tampil
    // dialog modal menyembunyikan isi halaman dari pohon aksesibilitas, jadi cek dengan hidden: true
    expect(await screen.findByRole("button", { name: "Tambah wadah", hidden: true })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Daftarkan alat", hidden: true })).not.toBeInTheDocument();
    expect(within(dialog).getByLabelText("Token alat")).toHaveValue("tok-rahasia-123");
    expect(within(dialog).getByText(/tidak akan ditampilkan lagi/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Sudah saya simpan" }));
    expect(screen.queryByRole("dialog", { name: "Token alat" })).not.toBeInTheDocument();
  });

  it("rotasi token meminta konfirmasi lalu menampilkan token baru", async () => {
    const user = userEvent.setup();
    let dikirim = 0;
    stub({
      tambahan: [
        http.post(`${API}/alat/al1/rotasi-token`, () => {
          dikirim += 1;
          return HttpResponse.json({ device_token: "tok-baru-456" });
        }),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Rotasi token" }));
    let dialog = await screen.findByRole("dialog", { name: "Buat token baru?" });
    await user.click(within(dialog).getByRole("button", { name: "Batal" }));
    expect(dikirim).toBe(0);
    await user.click(screen.getByRole("button", { name: "Rotasi token" }));
    dialog = await screen.findByRole("dialog", { name: "Buat token baru?" });
    await user.click(within(dialog).getByRole("button", { name: "Buat token baru" }));
    expect(await screen.findByRole("textbox", { name: "Token alat" })).toHaveValue("tok-baru-456");
  });

  it("tambah wadah memakai nomor berikutnya, ubah bahan, dan hapus yang ditolak", async () => {
    const user = userEvent.setup();
    let wadahBaru: unknown;
    let ubah: unknown;
    stub({
      tambahan: [
        http.post(`${API}/alat/al1/wadah`, async ({ request }) => {
          wadahBaru = await request.json();
          return HttpResponse.json({ id: "w3", alat_id: "al1", nomor_wadah: 3, bahan_pakan_id: "b2" }, { status: 201 });
        }),
        http.patch(`${API}/wadah/w2`, async ({ request }) => {
          ubah = await request.json();
          return HttpResponse.json({ id: "w2", alat_id: "al1", nomor_wadah: 2, bahan_pakan_id: "b2" });
        }),
        http.delete(`${API}/wadah/w1`, () => galat("Wadah pernah mengeluarkan pakan")),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Tambah wadah" }));
    let dialog = await screen.findByRole("dialog", { name: "Tambah wadah" });
    expect(within(dialog).getByLabelText("Nomor wadah")).toHaveValue("3");
    await vi.waitFor(() => expect(within(dialog).getByRole("option", { name: "Dedak" })).toBeInTheDocument());
    await user.selectOptions(within(dialog).getByLabelText("Bahan pakan"), "b2");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Wadah ditambahkan")).toBeInTheDocument();
    expect(wadahBaru).toEqual({ nomor_wadah: 3, bahan_pakan_id: "b2" });

    await user.click(screen.getByRole("button", { name: "Ubah bahan wadah 2" }));
    dialog = await screen.findByRole("dialog", { name: "Bahan wadah 2" });
    await vi.waitFor(() => expect(within(dialog).getByRole("option", { name: "Dedak" })).toBeInTheDocument());
    await user.selectOptions(within(dialog).getByLabelText("Bahan pakan"), "b2");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Bahan wadah disimpan")).toBeInTheDocument();
    expect(ubah).toEqual({ bahan_pakan_id: "b2" });

    await user.click(screen.getByRole("button", { name: "Hapus wadah 1" }));
    dialog = await screen.findByRole("dialog", { name: "Hapus data?" });
    await user.click(within(dialog).getByRole("button", { name: "Hapus" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("pernah mengeluarkan pakan");
  });

  it("Pekerja tidak melihat aksi alat, wadah, dan kandang", async () => {
    stub({ pengguna: PEKERJA });
    renderApp(detail, { masuk: true });
    expect(await screen.findByText("Wadah 1")).toBeInTheDocument();
    for (const nama of ["Ubah kandang", "Tambah wadah", "Rotasi token", "Hapus alat", "Ganti fase", "Hapus siklus"]) {
      expect(screen.queryByRole("button", { name: nama })).not.toBeInTheDocument();
    }
  });
});

describe("aksi stok", () => {
  it("isi ulang menerima kg dan mengirim gram; jumlah nol ditolak di klien", async () => {
    const user = userEvent.setup();
    const kirim: unknown[] = [];
    stub({
      tambahan: [
        http.post(`${API}/wadah/w1/stok/isi-ulang`, async ({ request }) => {
          kirim.push(await request.json());
          return HttpResponse.json({ id: "t1", wadah_id: "w1", dilakukan_oleh_id: PEMILIK.id, jenis: "ISI_ULANG", jumlah: 2500, dibuat_pada: "2026-11-02T00:00:00Z" }, { status: 201 });
        }),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Isi ulang Jagung" }));
    const dialog = await screen.findByRole("dialog", { name: "Isi ulang: Jagung" });
    await user.type(within(dialog).getByLabelText("Jumlah ditambahkan (kg)"), "0");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("lebih dari nol");
    expect(kirim).toHaveLength(0);
    const isi = within(dialog).getByLabelText("Jumlah ditambahkan (kg)");
    await user.clear(isi);
    await user.type(isi, "2,5");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Stok diisi ulang")).toBeInTheDocument();
    expect(kirim).toEqual([{ jumlah: 2500 }]);
  });

  it("koreksi mewajibkan alasan dan mengirim jumlah baru dalam gram", async () => {
    const user = userEvent.setup();
    const kirim: unknown[] = [];
    stub({
      pengguna: PEKERJA,
      tambahan: [
        http.post(`${API}/wadah/w2/stok/koreksi`, async ({ request }) => {
          kirim.push(await request.json());
          return HttpResponse.json({ id: "t2", wadah_id: "w2", dilakukan_oleh_id: PEKERJA.id, jenis: "KOREKSI_MANUAL", jumlah: 1500, dibuat_pada: "2026-11-02T00:00:00Z" }, { status: 201 });
        }),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Koreksi Dedak" }));
    const dialog = await screen.findByRole("dialog", { name: "Koreksi stok: Dedak" });
    await user.type(within(dialog).getByLabelText("Jumlah sebenarnya (kg)"), "1,5");
    // kosong: diblokir validasi bawaan browser; hanya spasi: ditolak oleh pesan kita
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(within(dialog).getByLabelText("Alasan")).toBeInvalid();
    await user.type(within(dialog).getByLabelText("Alasan"), "   ");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Alasan koreksi wajib diisi");
    expect(kirim).toHaveLength(0);
    await user.clear(within(dialog).getByLabelText("Alasan"));
    await user.type(within(dialog).getByLabelText("Alasan"), "Hitung ulang fisik");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Stok dikoreksi")).toBeInTheDocument();
    expect(kirim).toEqual([{ jumlah_baru: 1500, alasan: "Hitung ulang fisik" }]);
  });

  it("riwayat menampilkan jenis transaksi, jumlah, dan alasan", async () => {
    const user = userEvent.setup();
    stub({
      tambahan: [
        http.get(`${API}/wadah/w1/stok/transaksi`, () =>
          HttpResponse.json([
            { id: "t1", wadah_id: "w1", dilakukan_oleh_id: PEMILIK.id, jenis: "PENGELUARAN", jumlah: 760.21, alasan: null, dibuat_pada: "2026-11-02T08:00:00Z" },
            { id: "t2", wadah_id: "w1", dilakukan_oleh_id: PEMILIK.id, jenis: "KOREKSI_MANUAL", jumlah: 5000, alasan: "Opname", dibuat_pada: "2026-11-01T08:00:00Z" },
          ]),
        ),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Riwayat Jagung" }));
    const dialog = await screen.findByRole("dialog", { name: "Riwayat stok: Jagung" });
    expect(await within(dialog).findByText("Pengeluaran")).toBeInTheDocument();
    expect(within(dialog).getByText("760,21 g")).toBeInTheDocument();
    expect(within(dialog).getByText("Opname")).toBeInTheDocument();
    expect(within(dialog).getByText("5 kg")).toBeInTheDocument();
  });
});

describe("aksi siklus dan populasi", () => {
  it("mulai siklus: fase mengikuti jenis ayam, dikirim dengan angka dan tanggal", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub({
      siklus: null,
      tambahan: [
        http.post(`${API}/kandang/${ID}/siklus`, async ({ request }) => {
          body = await request.json();
          return HttpResponse.json(siklus, { status: 201 });
        }),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Mulai siklus" }));
    const dialog = await screen.findByRole("dialog", { name: "Mulai siklus" });
    await vi.waitFor(() => expect(within(dialog).getByRole("option", { name: "Broiler" })).toBeInTheDocument());
    await user.selectOptions(within(dialog).getByLabelText("Jenis ayam"), "j1");
    await vi.waitFor(() => expect(within(dialog).getByRole("option", { name: "Starter" })).toBeInTheDocument());
    const opsiFase = within(dialog).getAllByRole("option").map((o) => o.textContent);
    expect(opsiFase.indexOf("Starter")).toBeLessThan(opsiFase.indexOf("Grower"));
    await user.selectOptions(within(dialog).getByLabelText("Fase"), "f1");
    await user.type(within(dialog).getByLabelText("Jumlah ayam"), "100");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Siklus dimulai")).toBeInTheDocument();
    expect(body).toEqual({ jenis_ayam_id: "j1", fase_id: "f1", jumlah_ayam: 100, tanggal_mulai: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/) });
  });

  it("catat populasi (Pekerja boleh) mengirim jenis, jumlah, dan catatan", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub({
      pengguna: PEKERJA,
      tambahan: [
        http.post(`${API}/siklus/${SIKLUS}/populasi`, async ({ request }) => {
          body = await request.json();
          return HttpResponse.json({ id: "p2", siklus_id: SIKLUS, jenis: "MORTALITAS", jumlah: 2, tanggal: "2026-11-02", catatan: "Panas" }, { status: 201 });
        }),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Catat populasi" }));
    const dialog = await screen.findByRole("dialog", { name: "Catat perubahan populasi" });
    await user.type(within(dialog).getByLabelText("Jumlah (ekor)"), "2");
    await user.type(within(dialog).getByLabelText("Catatan (opsional)"), "Panas");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Perubahan populasi dicatat")).toBeInTheDocument();
    expect(body).toEqual({ jenis: "MORTALITAS", jumlah: 2, tanggal: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/), catatan: "Panas" });
  });

  it("ganti fase mengirim fase terpilih", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub({
      tambahan: [
        http.patch(`${API}/siklus/${SIKLUS}/fase`, async ({ request }) => {
          body = await request.json();
          return HttpResponse.json({ ...siklus, fase_id: "f2" });
        }),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Ganti fase" }));
    const dialog = await screen.findByRole("dialog", { name: "Ganti fase" });
    await vi.waitFor(() => expect(within(dialog).getByRole("option", { name: "Grower" })).toBeInTheDocument());
    await user.selectOptions(within(dialog).getByLabelText("Fase baru"), "f2");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Fase diganti")).toBeInTheDocument();
    expect(body).toEqual({ fase_id: "f2" });
  });

  it("koreksi siklus mengirim jumlah dan tanggal mulai", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub({
      tambahan: [
        http.patch(`${API}/siklus/${SIKLUS}`, async ({ request }) => {
          body = await request.json();
          return HttpResponse.json(siklus);
        }),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Koreksi siklus" }));
    const dialog = await screen.findByRole("dialog", { name: "Koreksi siklus" });
    const jumlah = within(dialog).getByLabelText("Jumlah ayam sekarang");
    expect(jumlah).toHaveValue("100");
    await user.clear(jumlah);
    await user.type(jumlah, "98");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Siklus dikoreksi")).toBeInTheDocument();
    expect(body).toEqual({ jumlah_ayam: 98, tanggal_mulai: "2026-10-01" });
  });

  it("selesaikan siklus meminta konfirmasi; hapus siklus yang ditolak menampilkan alasan", async () => {
    const user = userEvent.setup();
    let selesai = 0;
    stub({
      tambahan: [
        http.post(`${API}/siklus/${SIKLUS}/selesai`, () => {
          selesai += 1;
          return HttpResponse.json({ ...siklus, status: "SELESAI" });
        }),
        http.delete(`${API}/siklus/${SIKLUS}`, () => galat("Formulasi sudah dipakai perintah")),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Selesaikan siklus" }));
    let dialog = await screen.findByRole("dialog", { name: "Selesaikan siklus?" });
    await user.click(within(dialog).getByRole("button", { name: "Batal" }));
    expect(selesai).toBe(0);

    await user.click(screen.getByRole("button", { name: "Hapus siklus" }));
    dialog = await screen.findByRole("dialog", { name: "Hapus data?" });
    await user.click(within(dialog).getByRole("button", { name: "Hapus" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("sudah dipakai perintah");

    await user.click(within(dialog).getByRole("button", { name: "Batal" }));
    await user.click(screen.getByRole("button", { name: "Selesaikan siklus" }));
    dialog = await screen.findByRole("dialog", { name: "Selesaikan siklus?" });
    await user.click(within(dialog).getByRole("button", { name: "Selesaikan" }));
    expect(await screen.findByText("Siklus diselesaikan")).toBeInTheDocument();
    expect(selesai).toBe(1);
  });

  it("hapus catatan populasi (Pemilik) memanggil endpoint dengan id yang benar", async () => {
    const user = userEvent.setup();
    const hapus: string[] = [];
    stub({
      tambahan: [
        http.delete(`${API}/siklus/${SIKLUS}/populasi/p1`, () => {
          hapus.push("p1");
          return new HttpResponse(null, { status: 204 });
        }),
      ],
    });
    renderApp(detail, { masuk: true });
    await user.click(await screen.findByRole("button", { name: /Hapus catatan Mortalitas/ }));
    const dialog = await screen.findByRole("dialog", { name: "Hapus data?" });
    await user.click(within(dialog).getByRole("button", { name: "Hapus" }));
    expect(await screen.findByText("Catatan populasi dihapus")).toBeInTheDocument();
    expect(hapus).toEqual(["p1"]);
  });

  it("Pekerja tidak melihat Mulai siklus pada kandang kosong", async () => {
    stub({ pengguna: PEKERJA, siklus: null });
    renderApp(detail, { masuk: true });
    expect(await screen.findByText("Kandang kosong")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mulai siklus" })).not.toBeInTheDocument();
  });
});
