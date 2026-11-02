import { QueryClient } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "../app/AppRoutes";
import { AppProviders } from "../app/providers";
import { simpanToken } from "../auth/token";

export const API = "http://localhost:8000/api/v1";

export const PEMILIK = {
  id: "11111111-1111-1111-1111-111111111111",
  nama: "Pemilik Uji",
  email: "pemilik@example.com",
  role: "PEMILIK",
  status: "AKTIF",
  dibuat_pada: "2026-11-01T00:00:00Z",
};

/** Render seluruh aplikasi pada rute tertentu; `masuk: true` menyimpan token seolah sudah login. */
export function renderApp(rute = "/", opsi: { masuk?: boolean } = {}) {
  if (opsi.masuk) simpanToken("token-uji");
  // tanpa retry agar galat langsung terlihat dalam test
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <AppProviders client={client}>
      <MemoryRouter initialEntries={[rute]}>
        <AppRoutes />
      </MemoryRouter>
    </AppProviders>,
  );
}
