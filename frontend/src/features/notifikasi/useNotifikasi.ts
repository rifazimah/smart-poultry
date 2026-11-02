import { useQuery } from "@tanstack/react-query";
import { ambil, api, totalDariHeader } from "../../api/client";

/** Jumlah notifikasi belum dibaca, dari header X-Total-Count (cukup meminta 1 baris). */
export function useJumlahNotifikasiBelumDibaca() {
  return useQuery({
    queryKey: ["notifikasi", "belum-dibaca"],
    queryFn: async () => {
      const { response } = await ambil(
        api.GET("/api/v1/notifikasi", { params: { query: { status: "BELUM_DIBACA", limit: 1 } } }),
      );
      return totalDariHeader(response);
    },
    refetchInterval: 30_000, // polling jarang: notifikasi bukan data kritis waktu
  });
}
