import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../test/server";
import { API, PEMILIK, renderApp } from "../../test/render";

const PEKERJA = { ...PEMILIK, id: "22222222-2222-2222-2222-222222222222", nama: "Budi", role: "PEKERJA" };

const kandang = (id: string, nama: string, status = "AKTIF", lokasi: string | null = "Blok 1") => ({
  id,
  pemilik_id: PEMILIK.id,
  nama,
  lokasi,
  status,
});

function stub(pengguna = PEMILIK, notif = "0") {
  server.use(
    http.get(`${API}/auth/me`, () => HttpResponse.json(pengguna)),
    http.get(`${API}/notifikasi`, () => HttpResponse.json([], { headers: { "X-Total-Count": notif } })),
  );
}

describe("dashboard", () => {
  it("menampilkan daftar kandang dengan status dan total dari X-Total-Count", async () => {
    stub();
    server.use(
      http.get(`${API}/kandang`, () =>
        HttpResponse.json([kandang("a", "Kandang A"), kandang("b", "Kandang B", "NONAKTIF", null)], {
          headers: { "X-Total-Count": "2" },
        }),
      ),
    );
    renderApp("/", { masuk: true });
    expect(await screen.findByText("Kandang A")).toBeInTheDocument();
    expect(screen.getByText("Kandang B")).toBeInTheDocument();
    expect(screen.getByText("Blok 1")).toBeInTheDocument();
    expect(screen.getByText("Lokasi belum diisi")).toBeInTheDocument();
    expect(screen.getByText("Aktif")).toBeInTheDocument();
    expect(screen.getByText("Nonaktif")).toBeInTheDocument();
    expect(screen.getByText("2 kandang")).toBeInTheDocument();
  });

  it("meminta halaman pertama dengan skip=0 dan limit=20", async () => {
    stub();
    let url = "";
    server.use(
      http.get(`${API}/kandang`, ({ request }) => {
        url = request.url;
        return HttpResponse.json([], { headers: { "X-Total-Count": "0" } });
      }),
    );
    renderApp("/", { masuk: true });
    await screen.findByText("Belum ada kandang");
    const q = new URL(url).searchParams;
    expect(q.get("skip")).toBe("0");
    expect(q.get("limit")).toBe("20");
  });

  it("keadaan kosong berbeda untuk Pemilik dan Pekerja", async () => {
    stub();
    server.use(http.get(`${API}/kandang`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } })));
    const { unmount } = renderApp("/", { masuk: true });
    expect(await screen.findByText(/Tambah kandang untuk membuat/)).toBeInTheDocument();
    unmount();

    stub(PEKERJA);
    renderApp("/", { masuk: true });
    expect(await screen.findByText(/belum ditugaskan/i)).toBeInTheDocument();
  });

  it("galat server menampilkan pesan dan tombol coba lagi yang memuat ulang", async () => {
    const user = userEvent.setup();
    stub();
    let panggilan = 0;
    server.use(
      http.get(`${API}/kandang`, () => {
        panggilan += 1;
        return panggilan === 1
          ? HttpResponse.json({ detail: "boom" }, { status: 500 })
          : HttpResponse.json([kandang("a", "Kandang A")], { headers: { "X-Total-Count": "1" } });
      }),
    );
    renderApp("/", { masuk: true });
    expect(await screen.findByRole("alert")).toHaveTextContent("Terjadi kesalahan di server");
    await user.click(screen.getByRole("button", { name: "Coba lagi" }));
    expect(await screen.findByText("Kandang A")).toBeInTheDocument();
  });

  it("menampilkan jumlah notifikasi belum dibaca di header", async () => {
    stub(PEMILIK, "3");
    server.use(http.get(`${API}/kandang`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } })));
    renderApp("/", { masuk: true });
    expect(await screen.findByRole("img", { name: "Notifikasi belum dibaca: 3" })).toBeInTheDocument();
  });

  it("menu mengikuti peran dan nama pengguna tampil", async () => {
    stub(PEKERJA);
    server.use(http.get(`${API}/kandang`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } })));
    renderApp("/", { masuk: true });
    expect(await screen.findByText("Halo, Budi")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Dashboard" }).length).toBeGreaterThan(0);
    expect(screen.getByText("Pekerja")).toBeInTheDocument();
  });

  it("laci menu di ponsel dapat dibuka dan ditutup", async () => {
    const user = userEvent.setup();
    stub();
    server.use(http.get(`${API}/kandang`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } })));
    renderApp("/", { masuk: true });
    await user.click(await screen.findByRole("button", { name: "Buka menu" }));
    const laci = await screen.findByRole("dialog", { name: "Menu" });
    expect(laci).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tutup" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
