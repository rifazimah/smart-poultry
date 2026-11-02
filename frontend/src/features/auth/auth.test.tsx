import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { ambilToken } from "../../auth/token";
import { server } from "../../test/server";
import { API, PEMILIK, renderApp } from "../../test/render";

const notifikasi = http.get(`${API}/notifikasi`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } }));
const kandangKosong = http.get(`${API}/kandang`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } }));

async function isiDanKirim(email = "pemilik@example.com", sandi = "rahasia123") {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Kata sandi"), sandi);
  await user.click(screen.getByRole("button", { name: "Masuk" }));
}

describe("halaman masuk", () => {
  it("pengguna belum masuk diarahkan ke halaman masuk", async () => {
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Smart Poultry" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });

  it("tombol Masuk nonaktif sampai email dan kata sandi terisi", async () => {
    renderApp("/masuk");
    expect(screen.getByRole("button", { name: "Masuk" })).toBeDisabled();
  });

  it("login berhasil: kirim JSON, simpan token, tampilkan dashboard", async () => {
    let body: unknown;
    server.use(
      http.post(`${API}/auth/login`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ access_token: "token-baru", token_type: "bearer", user: PEMILIK });
      }),
      notifikasi,
      kandangKosong,
    );
    renderApp("/masuk");
    await isiDanKirim();
    expect(await screen.findByText("Halo, Pemilik Uji")).toBeInTheDocument();
    expect(body).toEqual({ email: "pemilik@example.com", kata_sandi: "rahasia123" });
    expect(ambilToken()).toBe("token-baru");
  });

  it("kredensial salah (401) menampilkan pesan server dan tidak menyimpan token", async () => {
    server.use(http.post(`${API}/auth/login`, () => HttpResponse.json({ detail: "Email atau kata sandi salah" }, { status: 401 })));
    renderApp("/masuk");
    await isiDanKirim("a@b.id", "salah");
    expect(await screen.findByRole("alert")).toHaveTextContent("Email atau kata sandi salah");
    expect(ambilToken()).toBeNull();
  });

  it("user nonaktif (403) menampilkan pesannya", async () => {
    server.use(http.post(`${API}/auth/login`, () => HttpResponse.json({ detail: "User nonaktif" }, { status: 403 })));
    renderApp("/masuk");
    await isiDanKirim();
    expect(await screen.findByRole("alert")).toHaveTextContent("User nonaktif");
  });

  it("terlalu banyak percobaan (429) menampilkan sisa waktu dari server", async () => {
    server.use(
      http.post(`${API}/auth/login`, () =>
        HttpResponse.json(
          { detail: "Terlalu banyak percobaan login yang gagal. Coba lagi dalam 120 detik." },
          { status: 429, headers: { "Retry-After": "120" } },
        ),
      ),
    );
    renderApp("/masuk");
    await isiDanKirim();
    expect(await screen.findByRole("alert")).toHaveTextContent("120 detik");
  });

  it("server tidak terjangkau menampilkan pesan koneksi", async () => {
    server.use(http.post(`${API}/auth/login`, () => HttpResponse.error()));
    renderApp("/masuk");
    await isiDanKirim();
    expect(await screen.findByRole("alert")).toHaveTextContent("Tidak dapat terhubung ke server");
  });

  it("kata sandi dapat ditampilkan dan disembunyikan", async () => {
    const user = userEvent.setup();
    renderApp("/masuk");
    const input = screen.getByLabelText("Kata sandi");
    expect(input).toHaveAttribute("type", "password");
    await user.click(screen.getByRole("button", { name: "Tampilkan kata sandi" }));
    expect(input).toHaveAttribute("type", "text");
    await user.click(screen.getByRole("button", { name: "Sembunyikan kata sandi" }));
    expect(input).toHaveAttribute("type", "password");
  });
});

describe("sesi", () => {
  it("token tersimpan dipulihkan lewat /auth/me", async () => {
    server.use(http.get(`${API}/auth/me`, () => HttpResponse.json(PEMILIK)), notifikasi, kandangKosong);
    renderApp("/", { masuk: true });
    expect(await screen.findByText("Halo, Pemilik Uji")).toBeInTheDocument();
  });

  it("token kedaluwarsa (401 pada /auth/me) membersihkan token dan kembali ke halaman masuk", async () => {
    server.use(http.get(`${API}/auth/me`, () => HttpResponse.json({ detail: "Could not validate credentials" }, { status: 401 })));
    renderApp("/", { masuk: true });
    expect(await screen.findByLabelText("Email")).toBeInTheDocument();
    expect(ambilToken()).toBeNull();
  });

  it("401 pada request lain saat sedang masuk memaksa keluar dan memberi tahu pengguna", async () => {
    server.use(
      http.get(`${API}/auth/me`, () => HttpResponse.json(PEMILIK)),
      notifikasi,
      http.get(`${API}/kandang`, () => HttpResponse.json({ detail: "Could not validate credentials" }, { status: 401 })),
    );
    renderApp("/", { masuk: true });
    expect(await screen.findByLabelText("Email")).toBeInTheDocument();
    expect(await screen.findByText("Sesi berakhir")).toBeInTheDocument();
    expect(ambilToken()).toBeNull();
  });

  it("Keluar menghapus token dan menampilkan halaman masuk", async () => {
    const user = userEvent.setup();
    server.use(http.get(`${API}/auth/me`, () => HttpResponse.json(PEMILIK)), notifikasi, kandangKosong);
    renderApp("/", { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Keluar" }));
    await waitFor(() => expect(screen.getByLabelText("Email")).toBeInTheDocument());
    expect(ambilToken()).toBeNull();
  });

  it("request terautentikasi membawa header Authorization", async () => {
    let header: string | null = null;
    server.use(
      http.get(`${API}/auth/me`, ({ request }) => {
        header = request.headers.get("Authorization");
        return HttpResponse.json(PEMILIK);
      }),
      notifikasi,
      kandangKosong,
    );
    renderApp("/", { masuk: true });
    await screen.findByText("Halo, Pemilik Uji");
    expect(header).toBe("Bearer token-uji");
  });
});
