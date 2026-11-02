import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ambil, api, type Skema } from "../../api/client";

export type Pekerja = Skema["UserPublic"];
export type Penugasan = Skema["PenugasanDetailPublic"];
export type PekerjaBaru = Skema["UserCreate"];

export function useDaftarPekerja() {
  return useQuery({
    queryKey: ["pekerja"],
    queryFn: async () => (await ambil(api.GET("/api/v1/users", { params: { query: { skip: 0, limit: 100 } } }))).data,
  });
}

export function useBuatPekerja() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: PekerjaBaru) => (await ambil(api.POST("/api/v1/users", { body: data }))).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pekerja"] }),
  });
}

export function useUbahStatusPekerja() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (v: { id: string; status: "AKTIF" | "NONAKTIF" }) =>
      (
        await ambil(
          api.PATCH("/api/v1/users/{id}/status", { params: { path: { id: v.id } }, body: { status: v.status } }),
        )
      ).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pekerja"] }),
  });
}

/** Penugasan yang masih berlaku untuk seorang pekerja. */
export function usePenugasanAktif(pekerjaId: string) {
  return useQuery({
    queryKey: ["pekerja", pekerjaId, "penugasan"],
    queryFn: async () =>
      (
        await ambil(
          api.GET("/api/v1/users/{id}/penugasan", {
            params: { path: { id: pekerjaId }, query: { status: "AKTIF", skip: 0, limit: 100 } },
          }),
        )
      ).data,
  });
}

export function useTugaskan(pekerjaId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { kandang_id: string; tanggal_mulai: string }) =>
      (await ambil(api.POST("/api/v1/users/{id}/penugasan", { params: { path: { id: pekerjaId } }, body: data }))).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pekerja", pekerjaId, "penugasan"] }),
  });
}

export function useAkhiriPenugasan(pekerjaId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await ambil(api.DELETE("/api/v1/penugasan/{id}", { params: { path: { id } } }));
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pekerja", pekerjaId, "penugasan"] }),
  });
}
