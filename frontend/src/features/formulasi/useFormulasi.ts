import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ambil, api, type Skema } from "../../api/client";

export type Preview = Skema["FormulasiPreview"];
export type FormulasiRingkas = Skema["FormulasiPublic"];
export type FormulasiLengkap = Skema["FormulasiLengkapPublic"];
export type ItemInput = Skema["FormulasiItemInput"];

export function useRiwayatFormulasi(siklusId: string) {
  return useQuery({
    queryKey: ["siklus", siklusId, "formulasi"],
    queryFn: async () =>
      (
        await ambil(
          api.GET("/api/v1/siklus/{id}/formulasi", {
            params: { path: { id: siklusId }, query: { skip: 0, limit: 20 } },
          }),
        )
      ).data,
  });
}

export function useDetailFormulasi(id: string | null) {
  return useQuery({
    queryKey: ["formulasi", id],
    enabled: !!id,
    queryFn: async () => (await ambil(api.GET("/api/v1/formulasi/{id}", { params: { path: { id: id! } } }))).data,
  });
}

/** Bahan pakan yang dapat dipilih pada formulasi manual. */
export function useBahanPakan() {
  return useQuery({
    queryKey: ["bahan-pakan", "pilihan"],
    queryFn: async () =>
      (await ambil(api.GET("/api/v1/bahan-pakan", { params: { query: { skip: 0, limit: 100 } } }))).data,
  });
}

export function useHitungOtomatis(siklusId: string) {
  return useMutation({
    mutationFn: async () =>
      (await ambil(api.POST("/api/v1/siklus/{id}/formulasi/otomatis", { params: { path: { id: siklusId } } }))).data,
  });
}

export function useHitungManual(siklusId: string) {
  return useMutation({
    mutationFn: async (item: ItemInput[]) =>
      (
        await ambil(
          api.POST("/api/v1/siklus/{id}/formulasi/manual", { params: { path: { id: siklusId } }, body: { item } }),
        )
      ).data,
  });
}

export function useSimpanFormulasi(siklusId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (preview: Preview) => (await ambil(api.POST("/api/v1/formulasi", { body: preview }))).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["siklus", siklusId, "formulasi"] }),
  });
}
