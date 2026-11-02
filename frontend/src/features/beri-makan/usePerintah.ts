import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ambil, api, type Skema } from "../../api/client";

export type Perintah = Skema["PerintahPublic"];
export type StatusPerintah = Skema["StatusPerintah"];

const SEDANG_JALAN: StatusPerintah[] = ["PENDING", "DIAMBIL", "BERJALAN"];
export const masihJalan = (s: StatusPerintah) => SEDANG_JALAN.includes(s);

/** Interval polling status perintah (ms); dipercepat pada test agar tidak menunggu lama. */
export const INTERVAL_POLLING = import.meta.env.MODE === "test" ? 50 : 3_000;

/** Riwayat perintah; dipoll hanya selama ada perintah yang belum selesai. */
export function useRiwayatPerintah(kandangId: string) {
  return useQuery({
    queryKey: ["kandang", kandangId, "perintah"],
    queryFn: async () =>
      (
        await ambil(
          api.GET("/api/v1/kandang/{id}/perintah", {
            params: { path: { id: kandangId }, query: { skip: 0, limit: 20 } },
          }),
        )
      ).data,
    refetchInterval: (query) => (query.state.data?.some((p) => masihJalan(p.status)) ? INTERVAL_POLLING : false),
  });
}

export function useBeriMakan(kandangId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (formulasiId: string) =>
      (
        await ambil(
          api.POST("/api/v1/kandang/{id}/perintah/beri-makan", {
            params: { path: { id: kandangId } },
            body: { formulasi_id: formulasiId },
          }),
        )
      ).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kandang", kandangId] }),
  });
}

export function useStopDarurat(kandangId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      (await ambil(api.POST("/api/v1/kandang/{id}/perintah/stop-darurat", { params: { path: { id: kandangId } } })))
        .data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kandang", kandangId] }),
  });
}
