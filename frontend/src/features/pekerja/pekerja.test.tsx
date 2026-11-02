import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../test/server";
import { API, PEMILIK, renderApp } from "../../test/render";

const BUDI = { id: "u1", nama: "Budi", email: "budi@example.com", role: "PEKERJA", status: "AKTIF", dibuat_pada: "2026-11-01T00:00:00Z" };
const SITI = { ...BUDI, id: "u2", nama: "Siti", email: "siti@example.com", status: "NONAKTIF" };
const kandang = (id: string, nama: string) => ({ id, pemilik_id: PEMILIK.id, nama, lokasi: null, status: "AKTIF" });

function stub(tambahan: Parameters<typeof server.use> = []) {
  server.use(
    http.get(`${API}/auth/me`, () => HttpResponse.json(PEMILIK)),
    http.get(`${API}/notifikasi`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } })),
    http.get(`${API}/users`, () => HttpResponse.json([BUDI, SITI])),
    http.get(`${API}/kandang`, () =>
      HttpResponse.json([kandang("k1", "Kandang A"), kandang("k2", "Kandang B")], { headers: { "X-Total-Count": "2" } }),
    ),
  );
  server.use(...tambahan);
}

describe("pekerja", () => {
  it("menampilkan daftar dengan status dan tombol sesuai status", async () => {
    stub();
    renderApp("/pekerja", { masuk: true });
    expect(await screen.findByText("Budi")).toBeInTheDocument();
    expect(screen.getByText("Siti")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nonaktifkan Budi" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aktifkan Siti" })).toBeInTheDocument();
  });

  it("menonaktifkan pekerja mengirim status baru", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub([
      http.patch(`${API}/users/u1/status`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...BUDI, status: "NONAKTIF" });
      }),
    ]);
    renderApp("/pekerja", { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Nonaktifkan Budi" }));
    expect(await screen.findByText("Pekerja dinonaktifkan")).toBeInTheDocument();
    expect(body).toEqual({ status: "NONAKTIF" });
  });

  it("tambah pekerja: kata sandi pendek ditolak di klien, lalu terkirim dengan role PEKERJA", async () => {
    const user = userEvent.setup();
    let body: unknown;
    stub([
      http.post(`${API}/users`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...BUDI, id: "u3", nama: "Dewi", email: "dewi@example.com" }, { status: 201 });
      }),
    ]);
    renderApp("/pekerja", { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Tambah pekerja" }));
    const dialog = await screen.findByRole("dialog", { name: "Tambah pekerja" });
    await user.type(within(dialog).getByLabelText("Nama"), "Dewi");
    await user.type(within(dialog).getByLabelText("Email"), "dewi@example.com");
    await user.type(within(dialog).getByLabelText("Kata sandi awal"), "pendek");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("minimal 8 karakter");
    expect(body).toBeUndefined();

    const sandi = within(dialog).getByLabelText("Kata sandi awal");
    await user.clear(sandi);
    await user.type(sandi, "rahasia123");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await screen.findByText("Pekerja ditambahkan")).toBeInTheDocument();
    expect(body).toEqual({ nama: "Dewi", email: "dewi@example.com", kata_sandi: "rahasia123", role: "PEKERJA" });
  });

  it("email yang sudah terdaftar menampilkan pesan server", async () => {
    const user = userEvent.setup();
    stub([http.post(`${API}/users`, () => HttpResponse.json({ detail: "Email sudah terdaftar" }, { status: 409 }))]);
    renderApp("/pekerja", { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Tambah pekerja" }));
    const dialog = await screen.findByRole("dialog", { name: "Tambah pekerja" });
    await user.type(within(dialog).getByLabelText("Nama"), "Budi 2");
    await user.type(within(dialog).getByLabelText("Email"), "budi@example.com");
    await user.type(within(dialog).getByLabelText("Kata sandi awal"), "rahasia123");
    await user.click(within(dialog).getByRole("button", { name: "Simpan" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Email sudah terdaftar");
  });

  it("penugasan: kandang yang sudah ditugaskan tidak ditawarkan; tugaskan dan akhiri", async () => {
    const user = userEvent.setup();
    let aktif = [
      { id: "p1", user_id: "u1", kandang_id: "k1", tanggal_mulai: "2026-10-01", status: "AKTIF", nama_pekerja: "Budi", email_pekerja: BUDI.email, nama_kandang: "Kandang A" },
    ];
    let tugas: unknown;
    const diakhiri: string[] = [];
    stub([
      http.get(`${API}/users/u1/penugasan`, () => HttpResponse.json(aktif)),
      http.post(`${API}/users/u1/penugasan`, async ({ request }) => {
        tugas = await request.json();
        return HttpResponse.json({ id: "p2", user_id: "u1", kandang_id: "k2", tanggal_mulai: "2026-11-02", status: "AKTIF" }, { status: 201 });
      }),
      http.delete(`${API}/penugasan/:id`, ({ params }) => {
        diakhiri.push(String(params.id));
        aktif = [];
        return new HttpResponse(null, { status: 204 });
      }),
    ]);
    renderApp("/pekerja", { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Penugasan Budi" }));
    const dialog = await screen.findByRole("dialog", { name: "Penugasan: Budi" });
    expect(await within(dialog).findByText("Kandang A")).toBeInTheDocument();
    await vi.waitFor(() => expect(within(dialog).getByRole("option", { name: "Kandang B" })).toBeInTheDocument());
    expect(within(dialog).queryByRole("option", { name: "Kandang A" })).not.toBeInTheDocument();

    await user.selectOptions(within(dialog).getByLabelText("Kandang"), "k2");
    await user.click(within(dialog).getByRole("button", { name: "Tugaskan" }));
    expect(await screen.findByText("Pekerja ditugaskan")).toBeInTheDocument();
    expect(tugas).toEqual({ kandang_id: "k2", tanggal_mulai: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/) });

    await user.click(within(dialog).getByRole("button", { name: "Akhiri penugasan Kandang A" }));
    expect(await screen.findByText("Penugasan diakhiri")).toBeInTheDocument();
    expect(diakhiri).toEqual(["p1"]);
  });

  it("penugasan ganda (409) menampilkan pesan server", async () => {
    const user = userEvent.setup();
    stub([
      http.get(`${API}/users/u1/penugasan`, () => HttpResponse.json([])),
      http.post(`${API}/users/u1/penugasan`, () =>
        HttpResponse.json({ detail: "Pekerja sudah ditugaskan ke kandang ini" }, { status: 409 }),
      ),
    ]);
    renderApp("/pekerja", { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Penugasan Budi" }));
    const dialog = await screen.findByRole("dialog", { name: "Penugasan: Budi" });
    await vi.waitFor(() => expect(within(dialog).getByRole("option", { name: "Kandang A" })).toBeInTheDocument());
    await user.selectOptions(within(dialog).getByLabelText("Kandang"), "k1");
    await user.click(within(dialog).getByRole("button", { name: "Tugaskan" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("sudah ditugaskan");
  });
});

describe("peran pekerja", () => {
  const PEKERJA = { ...PEMILIK, id: "u1", nama: "Budi", role: "PEKERJA" };

  it("Pekerja hanya melihat menu Dashboard dan Notifikasi, dan dialihkan dari /pekerja", async () => {
    server.use(
      http.get(`${API}/auth/me`, () => HttpResponse.json(PEKERJA)),
      http.get(`${API}/notifikasi`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } })),
      http.get(`${API}/kandang`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } })),
    );
    renderApp("/pekerja", { masuk: true });
    expect(await screen.findByText("Halo, Budi")).toBeInTheDocument();
    const menu = screen.getAllByRole("navigation", { name: "Menu utama" })[0];
    const label = within(menu).getAllByRole("link").map((a) => a.textContent);
    expect(label).toEqual(["Dashboard", "Notifikasi"]);
  });
});
