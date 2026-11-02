import { useQuery } from "@tanstack/react-query";
import { ambil, api, type Skema } from "../../api/client";

export type KandangDetail = Skema["KandangDetailPublic"];
export type AlatDetail = Skema["AlatDetailPublic"];
export type Stok = Skema["StokPublic"];
export type Siklus = Skema["SiklusKandangPublic"];
export type Populasi = Skema["PerubahanPopulasiPublic"];

export function useKandang(id: string) {
  return useQuery({
    queryKey: ["kandang", id],
    queryFn: async () => (await ambil(api.GET("/api/v1/kandang/{id}", { params: { path: { id } } }))).data,
  });
}

/** Kandang tanpa alat terdaftar dibalas `null` oleh server. */
export function useAlatKandang(id: string) {
  return useQuery({
    queryKey: ["kandang", id, "alat"],
    queryFn: async () => (await ambil(api.GET("/api/v1/kandang/{id}/alat", { params: { path: { id } } }))).data ?? null,
  });
}

export function useStokKandang(id: string) {
  return useQuery({
    queryKey: ["kandang", id, "stok"],
    queryFn: async () => (await ambil(api.GET("/api/v1/kandang/{id}/stok", { params: { path: { id } } }))).data,
  });
}

/** Siklus aktif, atau `null` bila kandang sedang kosong. */
export function useSiklusAktif(id: string) {
  return useQuery({
    queryKey: ["kandang", id, "siklus-aktif"],
    queryFn: async () =>
      (await ambil(api.GET("/api/v1/kandang/{id}/siklus/aktif", { params: { path: { id } } }))).data ?? null,
  });
}

export function useNamaJenisFase(siklus: Siklus | null | undefined) {
  const jenis = useQuery({
    queryKey: ["jenis-ayam", siklus?.jenis_ayam_id],
    enabled: !!siklus,
    queryFn: async () =>
      (await ambil(api.GET("/api/v1/jenis-ayam/{id}", { params: { path: { id: siklus!.jenis_ayam_id } } }))).data,
  });
  const fase = useQuery({
    queryKey: ["fase", siklus?.fase_id],
    enabled: !!siklus,
    queryFn: async () =>
      (await ambil(api.GET("/api/v1/fase/{id}", { params: { path: { id: siklus!.fase_id } } }))).data,
  });
  return { jenis: jenis.data, fase: fase.data };
}

export function usePopulasi(siklusId: string | undefined) {
  return useQuery({
    queryKey: ["siklus", siklusId, "populasi"],
    enabled: !!siklusId,
    queryFn: async () =>
      (
        await ambil(
          api.GET("/api/v1/siklus/{id}/populasi", {
            params: { path: { id: siklusId! }, query: { skip: 0, limit: 50 } },
          }),
        )
      ).data,
  });
}
