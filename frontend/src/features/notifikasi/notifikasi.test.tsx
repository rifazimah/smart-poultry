import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../test/server";
import { API, PEMILIK, renderApp } from "../../test/render";

const n = (id: string, status: string, jenis = "STOK_MENIPIS", judul = "Stok menipis") => ({
  id,
  user_id: PEMILIK.id,
  jenis,
  judul: `${judul} ${id}`,
  pesan: `Pesan ${id}`,
  status,
  dibuat_pada: "2026-11-02T08:00:00Z",
});

describe("notifikasi", () => {
  it("menampilkan daftar, menandai satu dibaca, dan menandai semua dibaca", async () => {
    const user = userEvent.setup();
    let daftar = [n("a", "BELUM_DIBACA"), n("b", "BELUM_DIBACA", "PERINTAH_GAGAL", "Gagal"), n("c", "SUDAH_DIBACA")];
    const dibaca: string[] = [];
    let semua = 0;
    server.use(
      http.get(`${API}/auth/me`, () => HttpResponse.json(PEMILIK)),
      http.get(`${API}/notifikasi`, ({ request }) => {
        const status = new URL(request.url).searchParams.get("status");
        const items = status ? daftar.filter((x) => x.status === status) : daftar;
        return HttpResponse.json(items, { headers: { "X-Total-Count": String(items.length) } });
      }),
      http.patch(`${API}/notifikasi/baca-semua`, () => {
        semua += 1;
        daftar = daftar.map((x) => ({ ...x, status: "SUDAH_DIBACA" }));
        return new HttpResponse(null, { status: 204 });
      }),
      http.patch(`${API}/notifikasi/:id/baca`, ({ params }) => {
        dibaca.push(String(params.id));
        daftar = daftar.map((x) => (x.id === params.id ? { ...x, status: "SUDAH_DIBACA" } : x));
        return HttpResponse.json(daftar.find((x) => x.id === params.id));
      }),
    );
    renderApp("/notifikasi", { masuk: true });
    expect(await screen.findByText("Stok menipis a")).toBeInTheDocument();
    expect(screen.getByText("Perintah gagal")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Tandai dibaca" })).toHaveLength(2);

    await user.click(screen.getAllByRole("button", { name: "Tandai dibaca" })[0]);
    expect(dibaca).toEqual(["a"]);
    await screen.findByText("Stok menipis a");
    await vi.waitFor(() => expect(screen.getAllByRole("button", { name: "Tandai dibaca" })).toHaveLength(1));

    await user.click(screen.getByRole("button", { name: "Tandai semua dibaca" }));
    await vi.waitFor(() => expect(screen.queryByRole("button", { name: "Tandai dibaca" })).not.toBeInTheDocument());
    expect(semua).toBe(1);
  });

  it("keadaan kosong dan menu memuat tautan Notifikasi", async () => {
    server.use(
      http.get(`${API}/auth/me`, () => HttpResponse.json(PEMILIK)),
      http.get(`${API}/notifikasi`, () => HttpResponse.json([], { headers: { "X-Total-Count": "0" } })),
    );
    renderApp("/notifikasi", { masuk: true });
    expect(await screen.findByText("Belum ada notifikasi")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Notifikasi" }).length).toBeGreaterThan(0);
  });
});
