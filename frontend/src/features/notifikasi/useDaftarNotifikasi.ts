import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ambil, api, totalDariHeader, type Skema } from "../../api/client";

export type Notifikasi = Skema["NotifikasiPublic"];

export function useDaftarNotifikasi() {
  return useQuery({
    queryKey: ["notifikasi", "daftar"],
    queryFn: async () => {
      const { data, response } = await ambil(api.GET("/api/v1/notifikasi", { params: { query: { skip: 0, limit: 50 } } }));
      return { items: data, total: totalDariHeader(response) };
    },
  });
}

function useSegarkan() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["notifikasi"] });
}

export function useTandaiBaca() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (id: string) =>
      (await ambil(api.PATCH("/api/v1/notifikasi/{id}/baca", { params: { path: { id } } }))).data,
    onSuccess: segarkan,
  });
}

export function useTandaiSemuaBaca() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async () => {
      await ambil(api.PATCH("/api/v1/notifikasi/baca-semua"));
    },
    onSuccess: segarkan,
  });
}
